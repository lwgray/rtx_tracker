#!/usr/bin/env python3
"""
Test script for Amazon scraper
"""

import os
import sys
from dotenv import load_dotenv
from database.db import init_db, get_session
from database.models import Retailer
from scrapers.amazon import scrape_amazon
from utils.logger import setup_logger

def main():
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    logger = setup_logger()
    logger.info("Starting Amazon scraper test")
    
    # Initialize the database
    init_db()
    
    # Get database session
    session = get_session()
    
    try:
        # Get or create Amazon retailer
        retailer = session.query(Retailer).filter_by(name="Amazon").first()
        if not retailer:
            logger.info("Creating Amazon retailer record")
            retailer = Retailer(
                name="Amazon",
                website="https://www.amazon.com"
            )
            session.add(retailer)
            session.commit()
        
        # Run the Amazon scraper
        results = scrape_amazon(session, retailer)
        
        # Print results
        if results:
            logger.info(f"Success! Found {len(results)} RTX 5090 products on Amazon:")
            for product, price, in_stock in results:
                logger.info(f" - {product.name}: ${price if price else 'N/A'} - {'In Stock' if in_stock else 'Out of Stock'}")
        else:
            logger.warning("No RTX 5090 products found on Amazon")
        
    except Exception as e:
        logger.error(f"Error in test script: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        session.close()
        logger.info("Test complete")

if __name__ == "__main__":
    main()
