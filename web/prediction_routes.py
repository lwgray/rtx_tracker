"""
API routes for RTX 5090 Stock Tracker predictions
"""

from flask import Blueprint, jsonify
import datetime
from database.db import get_session
from services.predictions import PricePredictionModel, StockPredictionModel
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

# Create blueprint
prediction_bp = Blueprint('predictions', __name__)

@prediction_bp.route('/api/price_predictions/<int:product_id>')
def price_predictions_api(product_id):
    """API endpoint for price predictions"""
    try:
        price_model = PricePredictionModel()
        prediction_result = price_model.predict(product_id)
        
        if not prediction_result:
            return jsonify({"error": "Failed to generate predictions"}), 404
        
        predictions, _ = prediction_result
        
        # Format predictions for JSON
        formatted_predictions = [
            {
                "date": date.strftime("%Y-%m-%d"),
                "price": round(price, 2)
            }
            for date, price in predictions
        ]
        
        return jsonify({"predictions": formatted_predictions})
    
    except Exception as e:
        logger.error(f"Error in price predictions API: {e}")
        return jsonify({"error": str(e)}), 500

@prediction_bp.route('/api/stock_predictions/<int:product_id>')
def stock_predictions_api(product_id):
    """API endpoint for stock predictions"""
    try:
        stock_model = StockPredictionModel()
        predictions = stock_model.predict(product_id)
        
        if not predictions:
            return jsonify({"error": "Failed to generate predictions"}), 404
        
        # Format predictions for JSON
        formatted_predictions = [
            {
                "date": date.strftime("%Y-%m-%d"),
                "probability": round(probability * 100, 1)
            }
            for date, probability in predictions
        ]
        
        return jsonify({"predictions": formatted_predictions})
    
    except Exception as e:
        logger.error(f"Error in stock predictions API: {e}")
        return jsonify({"error": str(e)}), 500