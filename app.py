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
from flask import Flask, render_template, redirect, url_for, request, jsonify, send_from_directory
import datetime

from config.settings import load_config
from database.db import init_db, get_session
from database.models import Product, PriceHistory, StockHistory, Retailer
from services.monitoring import monitor_rtx_5090, setup_scheduled_monitoring
from services.analysis import export_data_to_csv, generate_price_history_chart, generate_stock_history_chart
from services.predictions import predict_price_trend, predict_stock_availability, recommend_best_time_to_buy
from utils.exporters import export_all_data_to_zip
from utils.logger import setup_logger

# Create Flask app
def create_flask_app():
    """Create the Flask application for HTML templates"""
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        """Main dashboard view"""
        session = get_session()
        retailers = session.query(Retailer).all()
        
        # Get latest product data
        products_data = []
        for retailer in retailers:
            # Get products for this retailer
            products = session.query(Product).filter_by(retailer_id=retailer.id).all()
            
            for product in products:
                # Get latest price
                latest_price = session.query(PriceHistory)\
                    .filter_by(product_id=product.id)\
                    .order_by(PriceHistory.timestamp.desc())\
                    .first()
                
                # Get latest stock status
                latest_stock = session.query(StockHistory)\
                    .filter_by(product_id=product.id)\
                    .order_by(StockHistory.timestamp.desc())\
                    .first()
                
                products_data.append({
                    'id': product.id,
                    'name': product.name,
                    'manufacturer': product.manufacturer,
                    'retailer': retailer.name,
                    'price': latest_price.price if latest_price else None,
                    'in_stock': latest_stock.in_stock if latest_stock else False,
                    'url': product.url
                })
        
        session.close()
        
        current_year = datetime.datetime.now().year
        
        return render_template('index.html', 
                              retailers=retailers, 
                              products=products_data,
                              current_year=current_year)
    
    @app.route('/product/<int:product_id>')
    def product_detail(product_id):
        """Product detail view"""
        session = get_session()
        
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            session.close()
            return render_template('404.html'), 404
        
        # Get latest price
        latest_price = session.query(PriceHistory)\
            .filter_by(product_id=product.id)\
            .order_by(PriceHistory.timestamp.desc())\
            .first()
        
        # Get latest stock status
        latest_stock = session.query(StockHistory)\
            .filter_by(product_id=product.id)\
            .order_by(StockHistory.timestamp.desc())\
            .first()
        
        # Generate price history chart
        price_chart = generate_price_history_chart(product.id)
        
        # Generate stock history chart
        stock_chart = generate_stock_history_chart(product.id)
        
        # Generate price prediction
        prediction_result = predict_price_trend(product.id)
        prediction_chart = None
        predictions = None
        if prediction_result:
            prediction_chart, predictions = prediction_result
        
        # Generate stock prediction
        stock_prediction_result = predict_stock_availability(product.id)
        stock_prediction_chart = None
        stock_predictions = None
        if stock_prediction_result:
            stock_prediction_chart, stock_predictions = stock_prediction_result
        
        # Generate buying recommendation
        recommendation = recommend_best_time_to_buy(product.id)
        
        session.close()
        
        current_year = datetime.datetime.now().year
        
        return render_template('product_detail.html',
                              product=product,
                              current_price=latest_price.price if latest_price else None,
                              in_stock=latest_stock.in_stock if latest_stock else False,
                              price_chart=price_chart,
                              stock_chart=stock_chart,
                              prediction_chart=prediction_chart,
                              predictions=predictions,
                              stock_prediction_chart=stock_prediction_chart,
                              stock_predictions=stock_predictions,
                              recommendation=recommendation,
                              current_year=current_year)
    
    @app.route('/export_data')
    def export_data():
        """Export data to CSV files"""
        days = request.args.get('days', default=30, type=int)
        
        try:
            zip_filename = export_all_data_to_zip(days)
            if zip_filename:
                return send_from_directory(
                    os.path.dirname(os.path.abspath(zip_filename)),
                    os.path.basename(zip_filename),
                    as_attachment=True
                )
            else:
                return "Error exporting data", 500
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return str(e), 500
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors"""
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors"""
        return render_template('500.html'), 500
    
    return app

# Web dashboard (Dash app)
def start_dash_dashboard():
    """Start the Dash analytics dashboard"""
    from web.dashboard import app as dash_app
    # If running on Heroku, use the PORT environment variable
    port = int(os.environ.get('DASH_PORT', 8050))
    dash_app.run(debug=True, host='0.0.0.0', port=port)

# Run Flask app
def start_flask_app():
    """Start the Flask app for HTML templates"""
    flask_app = create_flask_app()
    port = int(os.environ.get('FLASK_PORT', 5003))
    flask_app.run(debug=True, host='0.0.0.0', port=port)

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
    parser.add_argument('--flask', action='store_true', help='Start the Flask web interface')
    parser.add_argument('--dash', action='store_true', help='Start the Dash analytics dashboard')
    parser.add_argument('--monitor', action='store_true', help='Start the monitoring system')
    parser.add_argument('--export', action='store_true', help='Export data to CSV files')
    parser.add_argument('--days', type=int, default=30, help='Number of days for export or charts')
    parser.add_argument('--ml-models', action='store_true', help='Train machine learning models')
    parser.add_argument('--all', action='store_true', help='Start all components (Flask, Dash, and monitoring)')
    
    args = parser.parse_args()
    
    if args.export:
        logger.info(f"Exporting data for the last {args.days} days")
        export_data_to_csv(args.days)
    elif args.ml_models:
        logger.info("Training machine learning models")
        from services.predictions import PricePredictionModel, StockPredictionModel
        
        # Get all product IDs from the database
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
    elif args.flask:
        logger.info("Starting Flask web interface")
        start_flask_app()
    elif args.dash:
        logger.info("Starting Dash analytics dashboard")
        start_dash_dashboard()
    elif args.monitor:
        logger.info("Starting monitoring service")
        monitor_rtx_5090()  # Run once
        setup_scheduled_monitoring()  # Then schedule
    elif args.all:
        logger.info("Starting all components (Flask, Dash, and monitoring)")
        
        # Start monitoring in a background thread
        monitor_thread = threading.Thread(target=setup_scheduled_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start Dash in a background thread
        dash_thread = threading.Thread(target=start_dash_dashboard)
        dash_thread.daemon = True
        dash_thread.start()
        
        # Start Flask in the main thread
        start_flask_app()
    else:
        # If no args specified, start Flask and monitoring service
        logger.info("Starting Flask web interface and monitoring service")
        
        # Start monitoring in a background thread
        monitor_thread = threading.Thread(target=setup_scheduled_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start Flask in the main thread
        start_flask_app()
