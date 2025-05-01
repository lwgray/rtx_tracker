#!/usr/bin/env python3
"""
RTX 5090 Stock Tracker
Main application entry point
"""

import argparse
import threading
import time
from dotenv import load_dotenv
import os
from flask import Flask

from config.settings import load_config
from database.db import init_db
from services.monitoring import monitor_rtx_5090, setup_scheduled_monitoring
from services.analysis import export_data_to_csv
from utils.logger import setup_logger

# Create Flask app
def create_flask_app():
    """Create the Flask application"""
    app = Flask(__name__)
    return app

# Web dashboard 
def create_web_dashboard():
    """Create and start the web dashboard"""
    # For the standard Flask interface
    from web.dashboard import create_app
    app = create_app()
    
    # For the Dash analytics dashboard
    # Since Dash is already creating its own server in dashboard.py,
    # we'll run the regular Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# Main entry point
if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    config = load_config()
    
    # Set up logging
    logger = setup_logger()
    logger.info("Starting RTX 5090 Stock Tracker")
    
    # Initialize the database
    init_db()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='RTX 5090 Stock Tracker')
    parser.add_argument('--dashboard', action='store_true', help='Start the web dashboard')
    parser.add_argument('--dash', action='store_true', help='Start the Dash analytics dashboard')
    parser.add_argument('--monitor', action='store_true', help='Start the monitoring system')
    parser.add_argument('--export', action='store_true', help='Export data to CSV files')
    parser.add_argument('--days', type=int, default=30, help='Number of days for export or charts')
    parser.add_argument('--ml-models', action='store_true', help='Train machine learning models')
    
    args = parser.parse_args()
    
    if args.export:
        logger.info(f"Exporting data for the last {args.days} days")
        export_data_to_csv(args.days)
    elif args.ml_models:
        logger.info("Training machine learning models")
        from services.predictions import PricePredictionModel, StockPredictionModel
        
        # Get all product IDs from the database
        from database.db import get_session
        from database.models import Product
        session = get_session()
        products = session.query(Product).all()
        session.close()
        
        # Train models for each product
        price_model = PricePredictionModel()
        stock_model = StockPredictionModel()
        
        for product in products:
            logger.info(f"Training models for product ID {product.id}")
            price_model.train(product.id, force_retrain=True)
            stock_model.train(product.id, force_retrain=True)
    elif args.dash:
        logger.info("Starting Dash analytics dashboard")
        # Import and run the Dash app directly
        from dashboard import app as dash_app
        dash_app.run_server(debug=True, host='0.0.0.0', port=8050)
    elif args.dashboard:
        logger.info("Starting web dashboard")
        create_web_dashboard()
    elif args.monitor:
        logger.info("Starting monitoring service")
        monitor_rtx_5090()  # Run once
        setup_scheduled_monitoring()  # Then schedule
    else:
        # If no args specified, start both monitoring and dashboard
        logger.info("Starting both monitoring service and web dashboard")
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=setup_scheduled_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start dashboard in main thread
        create_web_dashboard()