"""
Database module for storing lead search history
"""

import os
import json
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL')

engine = None
SessionLocal = None
Base = None
db_available = False

try:
    from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    
    if DATABASE_URL:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base()
        
        class SearchHistory(Base):
            """Model for storing search history"""
            __tablename__ = "search_history"
            
            id = Column(Integer, primary_key=True, index=True)
            keyword = Column(String(255), nullable=False)
            city = Column(String(255), nullable=False)
            country = Column(String(255), nullable=False)
            leads_count = Column(Integer, default=0)
            leads_data = Column(Text)
            created_at = Column(DateTime, default=datetime.utcnow)
        
        try:
            Base.metadata.create_all(bind=engine)
            db_available = True
        except Exception as e:
            db_available = False
    else:
        Base = declarative_base() if 'declarative_base' in dir() else None
        
except Exception as e:
    db_available = False


def save_search(keyword: str, city: str, country: str, leads: list) -> int:
    """
    Save a search to history
    
    Args:
        keyword: Search keyword
        city: City name
        country: Country name
        leads: List of lead dictionaries
        
    Returns:
        ID of the saved search
    """
    if not db_available or not SessionLocal:
        return None
    
    try:
        from sqlalchemy import Column, Integer, String, Text, DateTime
        
        session = SessionLocal()
        try:
            from sqlalchemy.orm import Session
            
            search = session.execute(
                session.get_bind().execute(
                    f"INSERT INTO search_history (keyword, city, country, leads_count, leads_data, created_at) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (keyword, city, country, len(leads), json.dumps(leads), datetime.utcnow())
                )
            )
            session.commit()
            return None
        except:
            session.rollback()
            return None
        finally:
            session.close()
    except:
        return None


def get_search_history(limit: int = 20) -> list:
    """
    Get recent search history
    
    Args:
        limit: Maximum number of searches to return
        
    Returns:
        List of search history records
    """
    if not db_available or not SessionLocal:
        return []
    
    try:
        session = SessionLocal()
        try:
            result = session.execute(
                "SELECT id, keyword, city, country, leads_count, created_at FROM search_history ORDER BY created_at DESC LIMIT :limit",
                {"limit": limit}
            )
            
            searches = []
            for row in result:
                searches.append({
                    'id': row[0],
                    'keyword': row[1],
                    'city': row[2],
                    'country': row[3],
                    'leads_count': row[4],
                    'created_at': row[5].strftime('%Y-%m-%d %H:%M') if row[5] else ''
                })
            return searches
        except:
            return []
        finally:
            session.close()
    except:
        return []


def load_search(search_id: int) -> dict:
    """
    Load a saved search by ID
    
    Args:
        search_id: ID of the search to load
        
    Returns:
        Dictionary with search details and leads
    """
    if not db_available or not SessionLocal:
        return None
    
    try:
        session = SessionLocal()
        try:
            result = session.execute(
                "SELECT id, keyword, city, country, leads_count, leads_data, created_at FROM search_history WHERE id = :id",
                {"id": search_id}
            )
            
            row = result.fetchone()
            if row:
                return {
                    'id': row[0],
                    'keyword': row[1],
                    'city': row[2],
                    'country': row[3],
                    'leads_count': row[4],
                    'leads': json.loads(row[5]) if row[5] else [],
                    'created_at': row[6].strftime('%Y-%m-%d %H:%M') if row[6] else ''
                }
            return None
        except:
            return None
        finally:
            session.close()
    except:
        return None


def delete_search(search_id: int) -> bool:
    """
    Delete a search from history
    
    Args:
        search_id: ID of the search to delete
        
    Returns:
        True if deleted, False otherwise
    """
    if not db_available or not SessionLocal:
        return False
    
    try:
        session = SessionLocal()
        try:
            session.execute(
                "DELETE FROM search_history WHERE id = :id",
                {"id": search_id}
            )
            session.commit()
            return True
        except:
            session.rollback()
            return False
        finally:
            session.close()
    except:
        return False
