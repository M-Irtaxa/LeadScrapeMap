"""
Google Maps Lead Generation Tool
Extract business leads from Google Maps with detailed contact information
"""

import streamlit as st
import pandas as pd
from google_maps_scraper import (
    scrape_google_maps, 
    scrape_bulk_searches,
    deduplicate_leads,
    filter_leads,
    leads_to_dataframe, 
    export_to_csv
)
from database import save_search, get_search_history, load_search, delete_search

st.set_page_config(
    page_title="Google Maps Lead Generation Tool",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
    }
    .stButton > button {
        width: 100%;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
        padding: 0.75rem;
        border-radius: 8px;
    }
    .stButton > button:hover {
        background-color: #ff3333;
    }
    .info-box {
        background-color: #1e3a5f;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #1a4d1a;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

if 'leads_data' not in st.session_state:
    st.session_state.leads_data = None
if 'raw_leads' not in st.session_state:
    st.session_state.raw_leads = []
if 'is_scraping' not in st.session_state:
    st.session_state.is_scraping = False
if 'bulk_searches' not in st.session_state:
    st.session_state.bulk_searches = [{'keyword': '', 'city': '', 'country': ''}]
if 'last_search_info' not in st.session_state:
    st.session_state.last_search_info = None

st.markdown("# 🎯 Google Maps Lead Generation Tool")
st.markdown("**Extract business leads from Google Maps with detailed contact information**")

main_tabs = st.tabs(["🔍 Search", "📚 History", "📖 Help"])

with main_tabs[0]:
    search_tabs = st.tabs(["Single Search", "Bulk Search"])
    
    with search_tabs[0]:
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown("### ⚙️ Search Settings")
            
            keyword = st.text_input(
                "Business Type/Keyword",
                placeholder="e.g., Cosmetics, Restaurant, Gym",
                help="Enter the type of business you're looking for",
                key="single_keyword"
            )
            
            city = st.text_input(
                "City",
                placeholder="e.g., Belfast",
                help="Specify the city where you want to find businesses",
                key="single_city"
            )
            
            country = st.text_input(
                "Country",
                placeholder="e.g., UK",
                help="Add the country name for better accuracy",
                key="single_country"
            )
            
            max_results = st.slider(
                "Maximum Results",
                min_value=10,
                max_value=100,
                value=20,
                step=5,
                help="Choose how many leads you want to extract (10-100)",
                key="single_max_results"
            )
            
            auto_dedupe = st.checkbox("Auto-deduplicate results", value=True, key="single_dedupe")
            
            st.info("⏱️ Scraping may take 1-2 minutes depending on results. Please wait...")
            
            search_button = st.button("🔍 Start Search", type="primary", disabled=st.session_state.is_scraping, key="single_search_btn")
            
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
        
        with col_right:
            with st.expander("📊 Extracted Data Includes", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - 🏢 **Business Name**
                    - 📍 **Full Address**
                    - 📞 **Phone Number**
                    - 💬 **WhatsApp Link** (if available)
                    - 📧 **Email** (if available)
                    """)
                with col2:
                    st.markdown("""
                    - 🌐 **Website**
                    - 🗺️ **Google Maps Link**
                    - ⭐ **Rating**
                    - 📝 **Reviews Count**
                    """)
        
        if search_button:
            if not keyword or not city or not country:
                st.error("Please fill in all required fields: Keyword, City, and Country")
            else:
                st.session_state.is_scraping = True
                
                with col_left:
                    progress_bar = progress_placeholder.progress(0)
                    
                    def update_progress(percent, message):
                        progress_bar.progress(percent / 100)
                        status_placeholder.markdown(f"**Status:** {message}")
                    
                    try:
                        leads = scrape_google_maps(
                            keyword=keyword,
                            city=city,
                            country=country,
                            max_results=max_results,
                            progress_callback=update_progress
                        )
                        
                        if auto_dedupe:
                            leads = deduplicate_leads(leads)
                        
                        if leads:
                            st.session_state.raw_leads = leads
                            st.session_state.leads_data = leads_to_dataframe(leads)
                            st.session_state.last_search_info = {
                                'keyword': keyword,
                                'city': city,
                                'country': country
                            }
                            
                            try:
                                save_search(keyword, city, country, leads)
                            except:
                                pass
                            
                            st.success(f"Successfully extracted {len(leads)} leads!")
                        else:
                            st.warning("No leads found. Try different search terms.")
                            
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                    
                    finally:
                        st.session_state.is_scraping = False
    
    with search_tabs[1]:
        st.markdown("### 📦 Bulk Search")
        st.markdown("Add multiple keyword/location combinations to search at once.")
        
        col_bulk_left, col_bulk_right = st.columns([2, 1])
        
        with col_bulk_left:
            for idx, search in enumerate(st.session_state.bulk_searches):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.session_state.bulk_searches[idx]['keyword'] = st.text_input(
                        "Keyword",
                        value=search.get('keyword', ''),
                        key=f"bulk_keyword_{idx}",
                        placeholder="e.g., Restaurant"
                    )
                with col2:
                    st.session_state.bulk_searches[idx]['city'] = st.text_input(
                        "City",
                        value=search.get('city', ''),
                        key=f"bulk_city_{idx}",
                        placeholder="e.g., London"
                    )
                with col3:
                    st.session_state.bulk_searches[idx]['country'] = st.text_input(
                        "Country",
                        value=search.get('country', ''),
                        key=f"bulk_country_{idx}",
                        placeholder="e.g., UK"
                    )
                with col4:
                    if idx > 0:
                        if st.button("🗑️", key=f"remove_bulk_{idx}"):
                            st.session_state.bulk_searches.pop(idx)
                            st.rerun()
            
            col_add, col_clear = st.columns(2)
            with col_add:
                if st.button("➕ Add Another Search"):
                    st.session_state.bulk_searches.append({'keyword': '', 'city': '', 'country': ''})
                    st.rerun()
            with col_clear:
                if st.button("🗑️ Clear All"):
                    st.session_state.bulk_searches = [{'keyword': '', 'city': '', 'country': ''}]
                    st.rerun()
        
        with col_bulk_right:
            bulk_max_results = st.slider(
                "Max Results per Search",
                min_value=10,
                max_value=100,
                value=20,
                step=5,
                key="bulk_max_results"
            )
            
            bulk_dedupe = st.checkbox("Deduplicate all results", value=True, key="bulk_dedupe")
            
            st.info(f"📊 Total searches: {len(st.session_state.bulk_searches)}")
        
        bulk_progress_placeholder = st.empty()
        bulk_status_placeholder = st.empty()
        
        if st.button("🚀 Start Bulk Search", type="primary", disabled=st.session_state.is_scraping, key="bulk_search_btn"):
            valid_searches = [s for s in st.session_state.bulk_searches 
                           if s.get('keyword') and s.get('city') and s.get('country')]
            
            if not valid_searches:
                st.error("Please add at least one complete search (keyword, city, and country).")
            else:
                st.session_state.is_scraping = True
                
                progress_bar = bulk_progress_placeholder.progress(0)
                
                def update_bulk_progress(percent, message):
                    progress_bar.progress(percent / 100)
                    bulk_status_placeholder.markdown(f"**Status:** {message}")
                
                try:
                    leads = scrape_bulk_searches(
                        searches=valid_searches,
                        max_results=bulk_max_results,
                        progress_callback=update_bulk_progress
                    )
                    
                    if bulk_dedupe:
                        leads = deduplicate_leads(leads)
                    
                    if leads:
                        st.session_state.raw_leads = leads
                        st.session_state.leads_data = leads_to_dataframe(leads)
                        st.session_state.last_search_info = {
                            'keyword': 'Bulk Search',
                            'city': f"{len(valid_searches)} locations",
                            'country': ''
                        }
                        
                        for search in valid_searches:
                            try:
                                search_leads = [l for l in leads if search['keyword'].lower() in l.get('Search Query', '').lower()]
                                save_search(search['keyword'], search['city'], search['country'], search_leads)
                            except:
                                pass
                        
                        st.success(f"Bulk search completed! Found {len(leads)} total leads.")
                    else:
                        st.warning("No leads found in any of the searches.")
                        
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                
                finally:
                    st.session_state.is_scraping = False

with main_tabs[1]:
    st.markdown("### 📚 Search History")
    st.markdown("View and load your previous searches.")
    
    history = get_search_history(limit=20)
    
    if history:
        for search in history:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(f"**{search['keyword']}** in {search['city']}, {search['country']}")
                st.caption(f"📅 {search['created_at']} | 📊 {search['leads_count']} leads")
            with col2:
                if st.button("📥 Load", key=f"load_{search['id']}"):
                    saved_search = load_search(search['id'])
                    if saved_search and saved_search['leads']:
                        st.session_state.raw_leads = saved_search['leads']
                        st.session_state.leads_data = leads_to_dataframe(saved_search['leads'])
                        st.session_state.last_search_info = {
                            'keyword': saved_search['keyword'],
                            'city': saved_search['city'],
                            'country': saved_search['country']
                        }
                        st.success(f"Loaded {saved_search['leads_count']} leads!")
                        st.rerun()
            with col3:
                csv_btn_key = f"download_history_{search['id']}"
                saved = load_search(search['id'])
                if saved and saved['leads']:
                    csv_data = export_to_csv(leads_to_dataframe(saved['leads']))
                    st.download_button(
                        label="📥 CSV",
                        data=csv_data,
                        file_name=f"leads_{search['keyword']}_{search['city']}.csv".replace(" ", "_"),
                        mime="text/csv",
                        key=csv_btn_key
                    )
            with col4:
                if st.button("🗑️", key=f"delete_{search['id']}"):
                    delete_search(search['id'])
                    st.rerun()
            
            st.markdown("---")
    else:
        st.info("No search history yet. Start searching to build your history!")

with main_tabs[2]:
    st.markdown("### 📖 How to Use")
    
    with st.expander("🔍 Single Search", expanded=True):
        st.markdown("""
        1. **Enter Keyword**: Type the business type you're looking for (e.g., Cosmetics, Restaurant, Gym)
        2. **Enter City**: Specify the city where you want to find businesses
        3. **Enter Country**: Add the country name for better accuracy
        4. **Set Max Results**: Choose how many leads you want to extract (10-100)
        5. **Click Start Search**: The tool will scrape Google Maps and extract business details
        """)
    
    with st.expander("📦 Bulk Search", expanded=True):
        st.markdown("""
        1. Add multiple keyword/location combinations
        2. Click "Add Another Search" to add more searches
        3. Set the maximum results per search
        4. Enable deduplication to remove duplicate businesses
        5. Click "Start Bulk Search" to process all searches
        """)
    
    with st.expander("🔧 Filtering Results", expanded=True):
        st.markdown("""
        After getting results, you can filter them by:
        - **Has Phone**: Show only businesses with phone numbers
        - **Has Website**: Show only businesses with websites
        - **Has Email**: Show only businesses with email addresses
        - **Has WhatsApp**: Show only businesses with WhatsApp links
        - **Minimum Rating**: Filter by minimum star rating
        """)
    
    with st.expander("📚 History Feature", expanded=True):
        st.markdown("""
        - All your searches are automatically saved
        - Access the History tab to view past searches
        - Load previous results instantly
        - Download CSV from history
        - Delete old searches you don't need
        """)

if st.session_state.leads_data is not None and not st.session_state.leads_data.empty:
    st.markdown("---")
    st.markdown("## 📋 Extracted Leads")
    
    with st.expander("🔧 Filter Options", expanded=False):
        filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)
        
        with filter_col1:
            filter_phone = st.selectbox(
                "Phone",
                options=[None, True, False],
                format_func=lambda x: "All" if x is None else ("Has Phone" if x else "No Phone"),
                key="filter_phone"
            )
        
        with filter_col2:
            filter_website = st.selectbox(
                "Website",
                options=[None, True, False],
                format_func=lambda x: "All" if x is None else ("Has Website" if x else "No Website"),
                key="filter_website"
            )
        
        with filter_col3:
            filter_email = st.selectbox(
                "Email",
                options=[None, True, False],
                format_func=lambda x: "All" if x is None else ("Has Email" if x else "No Email"),
                key="filter_email"
            )
        
        with filter_col4:
            filter_whatsapp = st.selectbox(
                "WhatsApp",
                options=[None, True, False],
                format_func=lambda x: "All" if x is None else ("Has WhatsApp" if x else "No WhatsApp"),
                key="filter_whatsapp"
            )
        
        with filter_col5:
            filter_rating = st.number_input(
                "Min Rating",
                min_value=0.0,
                max_value=5.0,
                value=0.0,
                step=0.5,
                key="filter_rating"
            )
        
        if st.button("Apply Filters", key="apply_filters"):
            filtered_df = filter_leads(
                st.session_state.leads_data,
                has_phone=filter_phone,
                has_website=filter_website,
                has_email=filter_email,
                has_whatsapp=filter_whatsapp,
                min_rating=filter_rating if filter_rating > 0 else None
            )
            st.session_state.leads_data = filtered_df
            st.rerun()
        
        if st.button("Reset Filters", key="reset_filters"):
            st.session_state.leads_data = leads_to_dataframe(st.session_state.raw_leads)
            st.rerun()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**Total Leads Found: {len(st.session_state.leads_data)}**")
    
    with col2:
        search_info = st.session_state.last_search_info or {}
        filename = f"leads_{search_info.get('keyword', 'search')}_{search_info.get('city', 'city')}.csv".replace(" ", "_")
        csv_data = export_to_csv(st.session_state.leads_data)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            key="download_main"
        )
    
    with col3:
        if st.button("🗑️ Clear Results", key="clear_results"):
            st.session_state.leads_data = None
            st.session_state.raw_leads = []
            st.session_state.last_search_info = None
            st.rerun()
    
    column_config = {
        "Business Name": st.column_config.TextColumn("Business Name", width="medium"),
        "Address": st.column_config.TextColumn("Address", width="large"),
        "Phone": st.column_config.TextColumn("Phone", width="small"),
        "WhatsApp Link": st.column_config.LinkColumn("WhatsApp", width="small"),
        "Website": st.column_config.LinkColumn("Website", width="small"),
        "Email": st.column_config.TextColumn("Email", width="small"),
        "Google Maps Link": st.column_config.LinkColumn("Maps Link", width="small"),
        "Rating": st.column_config.TextColumn("Rating", width="small"),
        "Reviews": st.column_config.TextColumn("Reviews", width="small"),
    }
    
    if 'Search Query' in st.session_state.leads_data.columns:
        column_config["Search Query"] = st.column_config.TextColumn("Search Query", width="medium")
    
    st.dataframe(
        st.session_state.leads_data,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    
    stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)
    
    with stat_col1:
        total_leads = len(st.session_state.leads_data)
        st.metric("Total Leads", total_leads)
    
    with stat_col2:
        with_phone = len(st.session_state.leads_data[st.session_state.leads_data['Phone'].str.len() > 0])
        st.metric("With Phone", with_phone)
    
    with stat_col3:
        with_website = len(st.session_state.leads_data[st.session_state.leads_data['Website'].str.len() > 0])
        st.metric("With Website", with_website)
    
    with stat_col4:
        if 'Email' in st.session_state.leads_data.columns:
            with_email = len(st.session_state.leads_data[st.session_state.leads_data['Email'].str.len() > 0])
        else:
            with_email = 0
        st.metric("With Email", with_email)
    
    with stat_col5:
        with_whatsapp = len(st.session_state.leads_data[st.session_state.leads_data['WhatsApp Link'].str.len() > 0])
        st.metric("With WhatsApp", with_whatsapp)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Google Maps Lead Generation Tool | Built with Streamlit</div>",
    unsafe_allow_html=True
)
