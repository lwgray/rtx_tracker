#!/usr/bin/env python3
"""
Ensure database and models are in sync for RTX 5090 Stock Tracker
"""

from sqlalchemy import inspect, text, Boolean
from database.db import get_engine, get_session
from database.models import Product, Retailer
from utils.logger import setup_logger

def sync_database_with_models():
    """Ensure database matches the current models"""
    logger = setup_logger()
    engine = get_engine()
    inspector = inspect(engine)
    
    # Check products table
    sync_table(engine, inspector, logger, Product, "products")
    
    # Check retailers table - specifically for 'active' column
    logger.info("Checking retailers table...")
    db_columns = [c["name"] for c in inspector.get_columns("retailers")]
    
    if "active" not in db_columns:
        logger.info("Adding 'active' column to retailers table")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE retailers ADD COLUMN active BOOLEAN DEFAULT TRUE"))
        logger.info("Added 'active' column successfully")
    else:
        logger.info("Column 'active' already exists in retailers table")

def sync_table(engine, inspector, logger, model_class, table_name):
    """Sync a specific table with its model"""
    # Check if the columns exist in the table
    db_columns = [c["name"] for c in inspector.get_columns(table_name)]
    logger.info(f"Database columns for {table_name}: {db_columns}")
    
    # Check if the attributes exist in the model
    model_columns = [c.key for c in inspect(model_class).mapper.column_attrs]
    logger.info(f"Model columns for {model_class.__name__}: {model_columns}")
    
    # Identify mismatches
    missing_in_db = [c for c in model_columns if c not in db_columns]
    missing_in_model = [c for c in db_columns if c not in model_columns]
    
    if missing_in_db:
        logger.warning(f"Columns in model but not in database: {missing_in_db}")
        for column in missing_in_db:
            # Add column to database based on model definition
            logger.info(f"Adding column {column} to database")
            attr = getattr(model_class.__table__.c, column)
            column_type = attr.type.compile(engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}"))
    
    if missing_in_model:
        logger.warning(f"Columns in database but not in model: {missing_in_model}")
        logger.warning(f"You may need to update your models.py file to include these columns")

if __name__ == "__main__":
    sync_database_with_models()
    print("Database synchronization completed!")