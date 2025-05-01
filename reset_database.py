#!/usr/bin/env python3
"""
Reset RTX 5090 Stock Tracker Database
"""

import argparse
import sys
from database.db import get_session, get_engine
from database.models import Base, Product, PriceHistory, StockHistory
from utils.logger import setup_logger

def confirm_deletion(operation_type):
    """
    Require explicit confirmation before proceeding with database operations
    
    Args:
        operation_type: Description of the operation being performed
    
    Returns:
        bool: True if confirmed, False otherwise
    """
    print(f"\n⚠️  WARNING: You are about to {operation_type}!")
    print("⚠️  This operation cannot be undone!")
    print("\nTo confirm, please type 'DELETE' (all caps): ")
    
    confirmation = input()
    
    if confirmation != "DELETE":
        print("Operation cancelled. Database remains unchanged.")
        return False
    
    return True

def reset_all():
    """Drop and recreate all tables"""
    if not confirm_deletion("reset the ENTIRE database (all data will be permanently lost)"):
        return
    
    logger.warning("Resetting entire database - all data will be lost!")
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    # Re-initialize retailers
    from database.db import init_db
    init_db()
    
    logger.info("Database has been completely reset")

def clear_price_history():
    """Clear only price history data"""
    if not confirm_deletion("delete ALL price history records"):
        return
    
    logger.warning("Clearing price history data")
    session = get_session()
    
    try:
        count = session.query(PriceHistory).delete()
        session.commit()
        logger.info(f"Deleted {count} price history records")
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error clearing price history: {e}")
    
    finally:
        session.close()

def clear_stock_history():
    """Clear only stock history data"""
    if not confirm_deletion("delete ALL stock history records"):
        return
    
    logger.warning("Clearing stock history data")
    session = get_session()
    
    try:
        count = session.query(StockHistory).delete()
        session.commit()
        logger.info(f"Deleted {count} stock history records")
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error clearing stock history: {e}")
    
    finally:
        session.close()

def clear_products():
    """Clear products (will also clear related price and stock history due to foreign key constraints)"""
    if not confirm_deletion("delete ALL products and their associated history records"):
        return
    
    logger.warning("Clearing products data - this will also clear price and stock history!")
    session = get_session()
    
    try:
        # First clear related history to avoid constraint issues
        session.query(PriceHistory).delete()
        session.query(StockHistory).delete()
        
        # Then clear products
        count = session.query(Product).delete()
        session.commit()
        logger.info(f"Deleted {count} products and all related history")
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error clearing products: {e}")
    
    finally:
        session.close()

if __name__ == "__main__":
    # Set up logging
    logger = setup_logger()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Reset RTX 5090 Stock Tracker Database')
    
    parser.add_argument('--all', action='store_true', help='Reset entire database (will delete all data)')
    parser.add_argument('--prices', action='store_true', help='Clear only price history')
    parser.add_argument('--stock', action='store_true', help='Clear only stock history')
    parser.add_argument('--products', action='store_true', help='Clear products (and related history)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt (DANGEROUS - use with caution)')
    
    args = parser.parse_args()
    
    # Override the confirm_deletion function if --force is used
    if args.force:
        confirm_deletion = lambda operation_type: True
        logger.warning("Force flag detected - skipping confirmation prompts!")
    
    if args.all:
        reset_all()
    elif args.prices:
        clear_price_history()
    elif args.stock:
        clear_stock_history()
    elif args.products:
        clear_products()
    else:
        parser.print_help()