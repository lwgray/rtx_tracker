#!/usr/bin/env python3
"""
Ensure database and models are in sync for RTX 5090 Stock Tracker
"""

from sqlalchemy import inspect, text
from database.db import get_engine, get_session
from database.models import Product
from utils.logger import setup_logger

def sync_database_with_models():
    """Ensure database matches the current models"""
    logger = setup_logger()
    engine = get_engine()
    inspector = inspect(engine)
    
    # Check if the column exists in the table
    db_columns = [c["name"] for c in inspector.get_columns("products")]
    logger.info(f"Database columns for products: {db_columns}")
    
    # Check if the attribute exists in the model
    model_columns = [c.key for c in inspect(Product).mapper.column_attrs]
    logger.info(f"Model columns for Product: {model_columns}")
    
    # Identify mismatches
    missing_in_db = [c for c in model_columns if c not in db_columns]
    missing_in_model = [c for c in db_columns if c not in model_columns]
    
    if missing_in_db:
        logger.warning(f"Columns in model but not in database: {missing_in_db}")
        for column in missing_in_db:
            # Add column to database based on model definition
            logger.info(f"Adding column {column} to database")
            attr = getattr(Product.__table__.c, column)
            column_type = attr.type.compile(engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE products ADD COLUMN {column} {column_type}"))
    
    if missing_in_model:
        logger.warning(f"Columns in database but not in model: {missing_in_model}")
        logger.warning("You may need to update your models.py file to include these columns")

if __name__ == "__main__":
    sync_database_with_models()
    print("Database synchronization completed!")