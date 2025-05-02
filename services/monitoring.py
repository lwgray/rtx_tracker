"""
Monitoring service for RTX 5090 Stock Tracker
"""

import time
import threading
import datetime
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
from database.monitoring_state import load_monitoring_state, update_run_timestamps

# Get logger
logger = get_logger(__name__)

# Global monitoring thread
monitoring_thread = None
monitoring_stop_event = threading.Event()

def monitor_rtx_5090():
    """
    Main function to monitor RTX 5090 availability and prices
    
    Scrapes data from all supported retailers and sends alerts when
    products are in stock and below price threshold
    """
    logger.info("Starting RTX 5090 monitoring cycle")
    
    # Load monitoring state to get price threshold
    state = load_monitoring_state()
    price_threshold = state.get('price_threshold', 2500)
    
    # Update last run timestamp
    update_run_timestamps()
    
    session = get_session()
    
    try:
        # Get all active retailers
        retailers = session.query(Retailer).filter_by(active=True).all()
        
        for retailer in retailers:
            try:
                logger.info(f"Scraping {retailer.name}")
                
                if retailer.name == "Best Buy":
                    product, price, in_stock = scrape_best_buy(session, retailer)
                    if product and price and in_stock and price < price_threshold:
                        send_email_alert(product, price, retailer.name)
                
                elif retailer.name == "Newegg":
                    results = scrape_newegg(session, retailer)
                    for product, price, in_stock in results:
                        if price and in_stock and price < price_threshold:
                            send_email_alert(product, price, retailer.name)
                
                elif retailer.name == "Amazon":
                    results = scrape_amazon(session, retailer)
                    for product, price, in_stock in results:
                        if price and in_stock and price < price_threshold:
                            send_email_alert(product, price, retailer.name)
                
                elif retailer.name == "Micro Center":
                    results = scrape_micro_center(session, retailer)
                    for product, price, in_stock in results:
                        if price and in_stock and price < price_threshold:
                            send_email_alert(product, price, retailer.name)
            
            except Exception as e:
                logger.error(f"Error scraping {retailer.name}: {e}")
        
        logger.info("Completed RTX 5090 monitoring cycle")
    
    except Exception as e:
        logger.error(f"Error in monitoring cycle: {e}")
    
    finally:
        session.close()

def setup_scheduled_monitoring():
    """
    Set up scheduled monitoring tasks based on configured interval
    """
    global monitoring_thread, monitoring_stop_event
    
    # Reset stop event
    monitoring_stop_event.clear()
    
    # Load monitoring state
    state = load_monitoring_state()
    interval = state.get('interval_minutes', 60)
    
    logger.info(f"Setting up scheduled monitoring (every {interval} minutes)")
    
    # Clear existing scheduled tasks
    schedule.clear()
    
    # Run immediately on startup
    if state.get('monitoring_active', True):
        monitor_rtx_5090()
    
    # Schedule runs at the configured interval
    schedule.every(interval).minutes.do(monitor_rtx_5090)
    
    # Start monitoring in a separate thread
    monitoring_thread = threading.Thread(target=run_scheduler, daemon=True)
    monitoring_thread.start()
    
    return monitoring_thread

def run_scheduler():
    """Run the scheduler loop"""
    # Keep running until stop event is set
    while not monitoring_stop_event.is_set():
        # Check if monitoring is active
        state = load_monitoring_state()
        if state.get('monitoring_active', True):
            schedule.run_pending()
        time.sleep(10)  # Check every 10 seconds for pending tasks

def stop_monitoring():
    """Stop the monitoring thread"""
    global monitoring_thread, monitoring_stop_event
    
    if monitoring_thread and monitoring_thread.is_alive():
        logger.info("Stopping monitoring thread")
        monitoring_stop_event.set()
        monitoring_thread.join(timeout=10)
        monitoring_thread = None
        return True
    return False

def restart_monitoring():
    """Restart the monitoring service with updated settings"""
    stop_monitoring()
    return setup_scheduled_monitoring()

def run_monitoring_now():
    """Run the monitoring cycle immediately"""
    try:
        logger.info("Manually triggering monitoring cycle")
        threading.Thread(target=monitor_rtx_5090, daemon=True).start()
        return True
    except Exception as e:
        logger.error(f"Error running monitoring now: {e}")
        return False