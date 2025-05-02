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
from flask import Flask, render_template, send_file, send_from_directory

from config.settings import load_config
from database.db import init_db, get_session
from database.models import Product, PriceHistory, StockHistory, Retailer
from services.monitoring import monitor_rtx_5090, setup_scheduled_monitoring
from services.analysis import export_data_to_csv, generate_price_history_chart, generate_stock_history_chart
from services.predictions import predict_price_trend, predict_stock_availability, recommend_best_time_to_buy
from utils.logger import setup_logger
from utils.exporters import export_all_data_to_zip
import datetime

# Create Flask app
def create_flask_app():
    """Create the Flask application"""
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
    
    # Ensure static/img directory exists
    static_img_dir = os.path.join(os.path.dirname(__file__), 'static', 'img')
    os.makedirs(static_img_dir, exist_ok=True)
    
    # Set up routes
    @app.route('/test')
    def test():
        return "Flask is working!"

    @app.route('/')
    def index():
        session = get_session()
        retailers = session.query(Retailer).all()
        
        # Get all products with their latest price and stock status
        products_data = []
        products = session.query(Product).all()
        
        for product in products:
            # Get latest price
            latest_price = session.query(PriceHistory)\
                .filter(PriceHistory.product_id == product.id)\
                .order_by(PriceHistory.timestamp.desc())\
                .first()
            
            # Get latest stock status
            latest_stock = session.query(StockHistory)\
                .filter(StockHistory.product_id == product.id)\
                .order_by(StockHistory.timestamp.desc())\
                .first()
            
            products_data.append({
                'id': product.id,
                'name': product.name,
                'manufacturer': product.manufacturer,
                'retailer': product.retailer.name,
                'price': latest_price.price if latest_price else None,
                'in_stock': latest_stock.in_stock if latest_stock else False,
                'url': product.url
            })
        
        session.close()
        
        # Get current year for the copyright notice
        current_year = datetime.datetime.now().year
        
        return render_template('index.html', retailers=retailers, products=products_data, current_year=current_year)
    
    @app.route('/export_data')
    def export_data():
        # Get current year for the copyright notice
        current_year = datetime.datetime.now().year
        return render_template('export_data.html', current_year=current_year)
        
    @app.route('/download_data/<int:days>')
    def download_data(days):
        filename = export_all_data_to_zip(days)
        return send_file(filename, as_attachment=True)
    
    @app.route('/product/<int:product_id>')
    def product_detail(product_id):
        # Check if static/img directory exists and is writable
        static_img_dir = os.path.join(os.path.dirname(__file__), 'static', 'img')
        if not os.path.exists(static_img_dir):
            try:
                os.makedirs(static_img_dir, exist_ok=True)
                logger.info(f"Created static/img directory at {static_img_dir}")
            except Exception as e:
                logger.error(f"Could not create static/img directory: {e}")
        
        try:
            # Verify read/write access by creating a test file
            test_file = os.path.join(static_img_dir, 'test_write.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            logger.error(f"Static directory is not writable: {e}")
        
        session = get_session()
        
        try:
            # Use session.get() with options to eager load the relationship
            from sqlalchemy.orm import selectinload
            from sqlalchemy import select
            
            # Create a select statement with eager loading of the retailer relationship
            stmt = select(Product).where(Product.id == product_id).options(selectinload(Product.retailer))
            product = session.execute(stmt).scalar_one_or_none()
            
            if not product:
                return render_template('404.html')
            
            # Get latest price and stock status
            latest_price = session.query(PriceHistory)\
                .filter(PriceHistory.product_id == product_id)\
                .order_by(PriceHistory.timestamp.desc())\
                .first()
            
            latest_stock = session.query(StockHistory)\
                .filter(StockHistory.product_id == product_id)\
                .order_by(StockHistory.timestamp.desc())\
                .first()
            
            # Generate charts
            # Add error handling for chart generation
            try:
                price_chart = generate_price_history_chart(product_id)
                # Verify the file actually exists
                if price_chart:
                    chart_path = os.path.join(os.path.dirname(__file__), 'static', 'img', price_chart)
                    if not os.path.exists(chart_path):
                        logger.error(f"Price chart file does not exist on disk: {chart_path}")
                        price_chart = None
            except Exception as e:
                logger.error(f"Error generating price chart: {e}")
                price_chart = None
                
            try:
                stock_chart = generate_stock_history_chart(product_id)
                # Verify the file actually exists
                if stock_chart:
                    chart_path = os.path.join(os.path.dirname(__file__), 'static', 'img', stock_chart)
                    if not os.path.exists(chart_path):
                        logger.error(f"Stock chart file does not exist on disk: {chart_path}")
                        stock_chart = None
            except Exception as e:
                logger.error(f"Error generating stock chart: {e}")
                stock_chart = None
            
            # Generate predictions
            prediction_result = predict_price_trend(product_id)
            stock_prediction_result = predict_stock_availability(product_id)
            recommendation = recommend_best_time_to_buy(product_id)
            
            prediction_chart = None
            predictions = None
            stock_prediction_chart = None
            stock_predictions = None
            
            if prediction_result:
                prediction_chart, predictions = prediction_result
            
            if stock_prediction_result:
                stock_prediction_chart, stock_predictions = stock_prediction_result
            
            current_year = datetime.datetime.now().year
            
            return render_template(
                'product_detail.html',
                product=product,
                current_price=latest_price.price if latest_price else None,
                in_stock=latest_stock.in_stock if latest_stock else False,
                price_chart=price_chart,
                stock_chart=stock_chart,
                prediction_chart=prediction_chart,
                stock_prediction_chart=stock_prediction_chart,
                predictions=predictions,
                stock_predictions=stock_predictions,
                recommendation=recommendation,
                current_year=current_year
            )
        except Exception as e:
            logger.error(f"Error displaying product details: {e}")
            return render_template('500.html')
        finally:
            session.close()
    
    # Error handling
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    # Serve static files
    @app.route('/static/<path:filename>')
    def static_files(filename):
        return send_from_directory(app.static_folder, filename)
    
    return app

# Run Flask app only
def run_flask():
    """Start the Flask web application without additional services"""
    logger.info("Starting Flask web interface")
    app = create_flask_app()
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=True)

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
    parser.add_argument('--flask', action='store_true', help='Start only the Flask web interface')
    parser.add_argument('--export', action='store_true', help='Export data to CSV files')
    parser.add_argument('--days', type=int, default=30, help='Number of days for export or charts')
    parser.add_argument('--ml-models', action='store_true', help='Train machine learning models')
    parser.add_argument('--port', type=int, default=5003, help='Port number for Flask')
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
        from web.dashboard import app as dash_app
        dash_app.run(debug=True, host='0.0.0.0', port=8050)
    elif args.flask:
        # New option to run only the Flask interface
        run_flask()
    elif args.dashboard:
        logger.info("Starting web dashboard")
        app = create_flask_app()
        port = int(os.environ.get('PORT', 5003))
        app.run(host='0.0.0.0', port=port)
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
        app = create_flask_app()
        port = args.port if args.port else int(os.environ.get('PORT', 5003))
        app.run(host='0.0.0.0', port=port)