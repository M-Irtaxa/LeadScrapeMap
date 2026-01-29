"""
Google Maps Lead Generation Scraper
Uses Selenium to scrape business information from Google Maps
"""

import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import streamlit as st


def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver



def extract_phone_number(text):
    """Extract phone number from text"""
    if not text:
        return ""
    phone_patterns = [
        r'\+?[\d\s\-\(\)]{10,}',
        r'\d{3}[\s\-]?\d{3}[\s\-]?\d{4}',
        r'\(\d{3}\)\s?\d{3}[\s\-]?\d{4}',
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group().strip()
    return ""


def create_whatsapp_link(phone):
    """Create WhatsApp link from phone number"""
    if not phone:
        return ""
    clean_phone = re.sub(r'[^\d+]', '', phone)
    if clean_phone:
        return f"https://wa.me/{clean_phone}"
    return ""


def extract_email(text):
    """Extract email address from text"""
    if not text:
        return ""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    if match:
        return match.group()
    return ""


def wait_for_element(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    """Wait for element to be present and return it"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        return None


def safe_find_element(driver, selector, by=By.CSS_SELECTOR):
    """Safely find an element, return None if not found"""
    try:
        return driver.find_element(by, selector)
    except (NoSuchElementException, StaleElementReferenceException):
        return None


def safe_find_elements(driver, selector, by=By.CSS_SELECTOR):
    """Safely find elements, return empty list if not found"""
    try:
        return driver.find_elements(by, selector)
    except (NoSuchElementException, StaleElementReferenceException):
        return []


def extract_business_details(driver):
    """Extract business details from the currently open business panel"""
    lead = {
        "Business Name": "",
        "Address": "",
        "Phone": "",
        "WhatsApp Link": "",
        "Website": "",
        "Email": "",
        "Google Maps Link": "",
        "Rating": "",
        "Reviews": ""
    }
    
    try:
        lead["Google Maps Link"] = driver.current_url
    except:
        pass
    
    name_selectors = [
        "h1.DUwDvf",
        "h1.fontHeadlineLarge",
        "div.lMbq3e h1",
        "h1"
    ]
    for selector in name_selectors:
        elem = safe_find_element(driver, selector)
        if elem and elem.text.strip():
            lead["Business Name"] = elem.text.strip()
            break
    
    address_selectors = [
        "button[data-item-id='address'] div.fontBodyMedium",
        "button[data-item-id='address']",
        "button[data-tooltip='Copy address'] div.fontBodyMedium",
        "div[data-item-id='address']"
    ]
    for selector in address_selectors:
        elem = safe_find_element(driver, selector)
        if elem:
            text = elem.text.strip() if elem.text else elem.get_attribute("aria-label")
            if text:
                lead["Address"] = text.replace("Address: ", "").strip()
                break
    
    phone_selectors = [
        "button[data-item-id^='phone:tel'] div.fontBodyMedium",
        "button[data-item-id^='phone'] div.fontBodyMedium",
        "button[data-tooltip='Copy phone number'] div.fontBodyMedium",
        "a[data-item-id^='phone']"
    ]
    for selector in phone_selectors:
        elem = safe_find_element(driver, selector)
        if elem:
            text = elem.text.strip() if elem.text else elem.get_attribute("aria-label")
            if text:
                lead["Phone"] = text.replace("Phone: ", "").strip()
                lead["WhatsApp Link"] = create_whatsapp_link(lead["Phone"])
                break
    
    website_selectors = [
        "a[data-item-id='authority']",
        "a[data-tooltip='Open website']",
        "a[aria-label*='website']"
    ]
    for selector in website_selectors:
        elem = safe_find_element(driver, selector)
        if elem:
            href = elem.get_attribute("href")
            if href and not href.startswith("https://www.google.com"):
                lead["Website"] = href
                break
    
    page_text = ""
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text
    except:
        pass
    
    if page_text:
        email = extract_email(page_text)
        if email:
            lead["Email"] = email
    
    rating_elem = safe_find_element(driver, "div.F7nice span[aria-hidden='true']")
    if rating_elem and rating_elem.text:
        lead["Rating"] = rating_elem.text.strip()
    
    reviews_elem = safe_find_element(driver, "div.F7nice span[aria-label*='review']")
    if reviews_elem:
        aria_label = reviews_elem.get_attribute("aria-label")
        if aria_label:
            lead["Reviews"] = aria_label
    
    return lead


def scroll_results_panel(driver, results_container, max_results, progress_callback=None):
    """Scroll the results panel to load more results"""
    last_count = 0
    scroll_attempts = 0
    max_scroll_attempts = 20
    
    while scroll_attempts < max_scroll_attempts:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_container)
        time.sleep(1.5)
        
        business_items = safe_find_elements(driver, "div.Nv2PK")
        current_count = len(business_items)
        
        if current_count >= max_results:
            break
        
        if current_count == last_count:
            scroll_attempts += 1
        else:
            scroll_attempts = 0
            last_count = current_count
        
        if progress_callback:
            progress = min(10 + (scroll_attempts * 2), 35)
            progress_callback(progress, f"Loading results... Found {current_count} businesses")
    
    return safe_find_elements(driver, "div.Nv2PK")


def scrape_google_maps(keyword: str, city: str, country: str, max_results: int = 20, progress_callback=None):
    """
    Scrape Google Maps for business leads
    
    Args:
        keyword: Business type/keyword to search
        city: City name
        country: Country name
        max_results: Maximum number of results to extract
        progress_callback: Function to update progress
        
    Returns:
        List of dictionaries containing business information
    """
    leads = []
    driver = None
    processed_names = set()
    
    try:
        search_query = f"{keyword} in {city}, {country}"
        maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        if progress_callback:
            progress_callback(0, "Starting browser...")
        
        driver = get_chrome_driver()
        driver.get(maps_url)
        
        time.sleep(4)
        
        if progress_callback:
            progress_callback(5, "Loading search results...")
        
        consent_buttons = safe_find_elements(driver, "button", By.TAG_NAME)
        for btn in consent_buttons:
            try:
                btn_text = btn.text.lower()
                if any(word in btn_text for word in ['accept', 'agree', 'i agree', 'accept all']):
                    btn.click()
                    time.sleep(2)
                    break
            except:
                continue
        
        time.sleep(2)
        
        results_container = None
        container_selectors = [
            "div[role='feed']",
            "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
            "div.m6QErb",
        ]
        
        for selector in container_selectors:
            results_container = safe_find_element(driver, selector)
            if results_container:
                break
        
        if not results_container:
            if progress_callback:
                progress_callback(0, "Could not find results container. Try different search terms.")
            return leads
        
        if progress_callback:
            progress_callback(10, "Scrolling to load more results...")
        
        scroll_results_panel(driver, results_container, max_results, progress_callback)
        
        if progress_callback:
            progress_callback(40, "Extracting business details...")
        
        business_cards = safe_find_elements(driver, "div.Nv2PK")
        total_cards = min(len(business_cards), max_results)
        
        if total_cards == 0:
            if progress_callback:
                progress_callback(0, "No businesses found. Try different search terms.")
            return leads
        
        for idx in range(total_cards):
            try:
                if progress_callback:
                    progress = 40 + int((idx / total_cards) * 55)
                    progress_callback(progress, f"Extracting lead {idx + 1} of {total_cards}...")
                
                business_cards = safe_find_elements(driver, "div.Nv2PK")
                
                if idx >= len(business_cards):
                    break
                
                card = business_cards[idx]
                
                link_element = safe_find_element(card, "a.hfpxzc")
                if not link_element:
                    continue
                
                business_name = link_element.get_attribute("aria-label") or ""
                
                if business_name in processed_names:
                    continue
                
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", link_element)
                    time.sleep(2.5)
                except Exception as click_error:
                    continue
                
                lead = extract_business_details(driver)
                
                if not lead["Business Name"] and business_name:
                    lead["Business Name"] = business_name
                
                if lead["Business Name"]:
                    processed_names.add(lead["Business Name"])
                    leads.append(lead)
                
                try:
                    back_button = safe_find_element(driver, "button[aria-label='Back']")
                    if back_button:
                        back_button.click()
                        time.sleep(1.5)
                except:
                    driver.back()
                    time.sleep(2)
                
                for selector in container_selectors:
                    results_container = safe_find_element(driver, selector)
                    if results_container:
                        break
                
                if not results_container:
                    driver.get(maps_url)
                    time.sleep(3)
                
            except Exception as e:
                try:
                    driver.get(maps_url)
                    time.sleep(3)
                except:
                    pass
                continue
        
        if progress_callback:
            progress_callback(100, f"Completed! Found {len(leads)} leads.")
        
    except Exception as e:
        error_msg = str(e)
        if progress_callback:
            progress_callback(0, f"Error: {error_msg}")
        raise e
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    return leads


def scrape_bulk_searches(searches: list, max_results: int = 20, progress_callback=None):
    """
    Scrape multiple keyword/location combinations
    
    Args:
        searches: List of dicts with 'keyword', 'city', 'country' keys
        max_results: Maximum results per search
        progress_callback: Function to update progress
        
    Returns:
        List of all leads from all searches
    """
    all_leads = []
    total_searches = len(searches)
    
    for idx, search in enumerate(searches):
        search_num = idx + 1
        
        def search_progress(percent, message):
            overall_percent = int((idx / total_searches) * 100 + (percent / total_searches))
            search_label = f"[Search {search_num}/{total_searches}] "
            if progress_callback:
                progress_callback(overall_percent, search_label + message)
        
        try:
            leads = scrape_google_maps(
                keyword=search.get('keyword', ''),
                city=search.get('city', ''),
                country=search.get('country', ''),
                max_results=max_results,
                progress_callback=search_progress
            )
            
            for lead in leads:
                lead['Search Query'] = f"{search.get('keyword', '')} in {search.get('city', '')}, {search.get('country', '')}"
            
            all_leads.extend(leads)
            
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error in search {search_num}: {str(e)}")
            continue
    
    if progress_callback:
        progress_callback(100, f"Bulk search completed! Found {len(all_leads)} total leads.")
    
    return all_leads


def deduplicate_leads(leads: list) -> list:
    """
    Remove duplicate leads based on business name and address
    
    Args:
        leads: List of lead dictionaries
        
    Returns:
        Deduplicated list of leads
    """
    seen = set()
    unique_leads = []
    
    for lead in leads:
        key = (lead.get('Business Name', '').lower().strip(), 
               lead.get('Address', '').lower().strip())
        
        if key[0] and key not in seen:
            seen.add(key)
            unique_leads.append(lead)
    
    return unique_leads


def filter_leads(df: pd.DataFrame, 
                 has_phone: bool = None,
                 has_website: bool = None,
                 has_email: bool = None,
                 has_whatsapp: bool = None,
                 min_rating: float = None) -> pd.DataFrame:
    """
    Filter leads based on criteria
    
    Args:
        df: DataFrame of leads
        has_phone: Filter for leads with/without phone
        has_website: Filter for leads with/without website
        has_email: Filter for leads with/without email
        has_whatsapp: Filter for leads with/without WhatsApp
        min_rating: Minimum rating filter
        
    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    if has_phone is not None:
        if has_phone:
            filtered_df = filtered_df[filtered_df['Phone'].str.len() > 0]
        else:
            filtered_df = filtered_df[filtered_df['Phone'].str.len() == 0]
    
    if has_website is not None:
        if has_website:
            filtered_df = filtered_df[filtered_df['Website'].str.len() > 0]
        else:
            filtered_df = filtered_df[filtered_df['Website'].str.len() == 0]
    
    if has_email is not None:
        if 'Email' in filtered_df.columns:
            if has_email:
                filtered_df = filtered_df[filtered_df['Email'].str.len() > 0]
            else:
                filtered_df = filtered_df[filtered_df['Email'].str.len() == 0]
    
    if has_whatsapp is not None:
        if has_whatsapp:
            filtered_df = filtered_df[filtered_df['WhatsApp Link'].str.len() > 0]
        else:
            filtered_df = filtered_df[filtered_df['WhatsApp Link'].str.len() == 0]
    
    if min_rating is not None and 'Rating' in filtered_df.columns:
        def parse_rating(val):
            try:
                return float(str(val).replace(',', '.'))
            except:
                return 0.0
        
        filtered_df = filtered_df[filtered_df['Rating'].apply(parse_rating) >= min_rating]
    
    return filtered_df


def leads_to_dataframe(leads: list) -> pd.DataFrame:
    """Convert leads list to pandas DataFrame"""
    if not leads:
        return pd.DataFrame()
    
    df = pd.DataFrame(leads)
    return df


def export_to_csv(df: pd.DataFrame, filename: str = "leads.csv") -> str:
    """Export DataFrame to CSV and return the content"""
    return df.to_csv(index=False)
