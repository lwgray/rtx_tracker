"""
Database connection utilities for the RTX 5090 Stock Tracker
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from database.models import Base
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

def get_database_url():
    """Get database URL from environment variables or use default"""
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rtx_tracker")
    
    # Handle Heroku's updated DATABASE_URL format
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    return DATABASE_URL

def get_engine():
    """Create and return a database engine"""
    DATABASE_URL = get_database_url()
    logger.debug(f"Connecting to database: {DATABASE_URL}")
    
    engine = create_engine(DATABASE_URL)
    return engine

def get_session():
    """Create and return a database session"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db():
    """Initialize the database, creating tables if they don't exist"""
    logger.info("Initializing database")
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    # Ensure retailers exist in the database
    session = get_session()
    from database.models import Retailer
    
    retailers = {
        "Best Buy": "https://www.bestbuy.com",
        "Newegg": "https://www.newegg.com",
        "Amazon": "https://www.amazon.com",
        "NVIDIA": "https://www.nvidia.com",
        "Micro Center": "https://www.microcenter.com",
        "B&H Photo": "https://www.bhphotovideo.com"
    }
    
    for name, website in retailers.items():
        retailer = session.query(Retailer).filter_by(name=name).first()
        if not retailer:
            retailer = Retailer(name=name, website=website)
            session.add(retailer)
            logger.info(f"Added retailer: {name}")
    
    session.commit()
    session.close()
    
    logger.info("Database initialization complete")