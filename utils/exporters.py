"""
Data export utilities for RTX 5090 Stock Tracker
"""

import os
import datetime
import pandas as pd
import zipfile
from database.db import get_session
from database.models import Product, PriceHistory, StockHistory, Retailer
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

def export_to_csv(data, filename):
    """
    Export data to CSV file
    
    Args:
        data: DataFrame to export
        filename: Name of the CSV file
    """
    try:
        data.to_csv(filename, index=False)
        logger.info(f"Data exported to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error exporting data to {filename}: {e}")
        return False

def export_products_to_csv(days=30, filename="export_products.csv"):
    """
    Export products to CSV file
    
    Args:
        days: Number of days of data to export
        filename: Name of the CSV file
        
    Returns:
        bool: True if export was successful, False otherwise
    """
    session = get_session()
    
    try:
        # Get all products
        products = session.query(Product).all()
        
        # Format product data
        product_data = [{
            'id': p.id,
            'retailer': p.retailer.name,
            'name': p.name,
            'manufacturer': p.manufacturer,
            'url': p.url,
            'created_at': p.created_at,
            'updated_at': p.updated_at
        } for p in products]
        
        # Create DataFrame
        df = pd.DataFrame(product_data)
        
        # Export to CSV
        return export_to_csv(df, filename)
    
    except Exception as e:
        logger.error(f"Error exporting products to CSV: {e}")
        return False
    
    finally:
        session.close()

def export_price_history_to_csv(days=30, filename="export_price_history.csv"):
    """
    Export price history to CSV file
    
    Args:
        days: Number of days of data to export
        filename: Name of the CSV file
        
    Returns:
        bool: True if export was successful, False otherwise
    """
    session = get_session()
    
    try:
        # Calculate date range
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get price history
        price_history = session.query(PriceHistory)\
            .filter(PriceHistory.timestamp >= start_date)\
            .order_by(PriceHistory.timestamp).all()
        
        # Format price history data
        price_data = []
        for ph in price_history:
            product = session.query(Product).filter_by(id=ph.product_id).first()
            if product:
                price_data.append({
                    'product_id': ph.product_id,
                    'product_name': product.name,
                    'manufacturer': product.manufacturer,
                    'retailer': product.retailer.name,
                    'price': ph.price,
                    'currency': ph.currency,
                    'timestamp': ph.timestamp
                })
        
        # Create DataFrame
        df = pd.DataFrame(price_data)
        
        # Export to CSV
        return export_to_csv(df, filename)
    
    except Exception as e:
        logger.error(f"Error exporting price history to CSV: {e}")
        return False
    
    finally:
        session.close()

def export_stock_history_to_csv(days=30, filename="export_stock_history.csv"):
    """
    Export stock history to CSV file
    
    Args:
        days: Number of days of data to export
        filename: Name of the CSV file
        
    Returns:
        bool: True if export was successful, False otherwise
    """
    session = get_session()
    
    try:
        # Calculate date range
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get stock history
        stock_history = session.query(StockHistory)\
            .filter(StockHistory.timestamp >= start_date)\
            .order_by(StockHistory.timestamp).all()
        
        # Format stock history data
        stock_data = []
        for sh in stock_history:
            product = session.query(Product).filter_by(id=sh.product_id).first()
            if product:
                stock_data.append({
                    'product_id': sh.product_id,
                    'product_name': product.name,
                    'manufacturer': product.manufacturer,
                    'retailer': product.retailer.name,
                    'in_stock': sh.in_stock,
                    'timestamp': sh.timestamp
                })
        
        # Create DataFrame
        df = pd.DataFrame(stock_data)
        
        # Export to CSV
        return export_to_csv(df, filename)
    
    except Exception as e:
        logger.error(f"Error exporting stock history to CSV: {e}")
        return False
    
    finally:
        session.close()

def export_all_data_to_zip(days=30, filename=None):
    """
    Export all data to a zip file
    
    Args:
        days: Number of days of data to export
        filename: Name of the zip file (default: rtx_tracker_data_TIMESTAMP.zip)
        
    Returns:
        str: Path to the zip file or None if failed
    """
    if filename is None:
        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"rtx_tracker_data_{timestamp}.zip"
    
    try:
        # Export individual CSV files
        export_products_to_csv(days)
        export_price_history_to_csv(days)
        export_stock_history_to_csv(days)
        
        # Create zip file
        with zipfile.ZipFile(filename, 'w') as zipf:
            zipf.write('export_products.csv')
            zipf.write('export_price_history.csv')
            zipf.write('export_stock_history.csv')
        
        logger.info(f"Data exported to {filename}")
        return filename
    
    except Exception as e:
        logger.error(f"Error exporting data to zip: {e}")
        return None