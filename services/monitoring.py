"""
Monitoring service for RTX 5090 Stock Tracker
"""

import time
import schedule
from database.db import get_session
from database.models import Retailer
from scrapers.best_buy import scrape_best_buy
from scrapers.newegg import scrape_newegg
from scrapers.amazon import scrape_amazon
from scrapers.micro_center import scrape_micro_center
# Removed B&H Photo import
from services.alerts import send_email_alert
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

def monitor_rtx_5090():
    """
    Main function to monitor RTX 5090 availability and prices
    
    Scrapes data from all supported retailers and sends alerts when
    products are in stock and below price threshold
    """
    logger.info("Starting RTX 5090 monitoring cycle")
    
    session = get_session()
    
    try:
        # Best Buy
        best_buy = session.query(Retailer).filter_by(name="Best Buy").first()
        product, price, in_stock = scrape_best_buy(session, best_buy)
        if product and price and in_stock and price < 2500:
            send_email_alert(product, price, "Best Buy")
        
        # Newegg
        newegg = session.query(Retailer).filter_by(name="Newegg").first()
        newegg_results = scrape_newegg(session, newegg)
        for product, price, in_stock in newegg_results:
            if price and in_stock and price < 2500:
                send_email_alert(product, price, "Newegg")
        
        # Amazon
        amazon = session.query(Retailer).filter_by(name="Amazon").first()
        amazon_results = scrape_amazon(session, amazon)
        for product, price, in_stock in amazon_results:
            if price and in_stock and price < 2500:
                send_email_alert(product, price, "Amazon")
        
        # Micro Center
        micro_center = session.query(Retailer).filter_by(name="Micro Center").first()
        micro_center_results = scrape_micro_center(session, micro_center)
        for product, price, in_stock in micro_center_results:
            if price and in_stock and price < 2500:
                send_email_alert(product, price, "Micro Center")
        
        # B&H Photo section removed
        
        logger.info("Completed RTX 5090 monitoring cycle")
    
    except Exception as e:
        logger.error(f"Error in monitoring cycle: {e}")
    
    finally:
        session.close()

def setup_scheduled_monitoring():
    """
    Set up scheduled monitoring tasks
    
    Runs the monitoring cycle every hour
    """
    logger.info("Setting up scheduled monitoring (hourly)")
    
    # Run immediately on startup
    monitor_rtx_5090()
    
    # Schedule hourly runs
    schedule.every(1).hour.do(monitor_rtx_5090)
    
    # Keep running indefinitely
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute for pending tasks