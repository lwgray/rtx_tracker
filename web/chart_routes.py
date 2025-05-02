"""
Dynamic chart generation routes for RTX 5090 Stock Tracker
"""

import io
from flask import Blueprint, send_file, jsonify, make_response
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import pandas as pd
import datetime
from sqlalchemy import func
from database.db import get_session
from database.models import Product, PriceHistory, StockHistory
from services.predictions import PricePredictionModel, StockPredictionModel
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

# Create blueprint
chart_bp = Blueprint('charts', __name__)

@chart_bp.route('/charts/price_history/<int:product_id>')
def price_history_chart(product_id):
    """Generate price history chart for a product"""
    try:
        fig = generate_price_history_chart(product_id)
        if fig is None:
            return make_response(jsonify({"error": "Not enough data"}), 404)
        
        # Convert the figure to a PNG image
        img_bytes = fig.to_image(format="png")
        
        # Create a file-like object from the bytes
        img_io = io.BytesIO(img_bytes)
        img_io.seek(0)
        
        # Send the file with the appropriate MIME type
        return send_file(img_io, mimetype='image/png')
    
    except Exception as e:
        logger.error(f"Error generating price history chart: {e}")
        return make_response(jsonify({"error": str(e)}), 500)

@chart_bp.route('/charts/stock_history/<int:product_id>')
def stock_history_chart(product_id):
    """Generate stock history chart for a product"""
    try:
        fig = generate_stock_history_chart(product_id)
        if fig is None:
            return make_response(jsonify({"error": "Not enough data"}), 404)
        
        # Convert the figure to a PNG image
        img_bytes = fig.to_image(format="png")
        
        # Create a file-like object from the bytes
        img_io = io.BytesIO(img_bytes)
        img_io.seek(0)
        
        # Send the file with the appropriate MIME type
        return send_file(img_io, mimetype='image/png')
    
    except Exception as e:
        logger.error(f"Error generating stock history chart: {e}")
        return make_response(jsonify({"error": str(e)}), 500)

@chart_bp.route('/charts/price_prediction/<int:product_id>')
def price_prediction_chart(product_id):
    """Generate price prediction chart for a product"""
    try:
        fig, predictions = generate_price_prediction_chart(product_id)
        if fig is None:
            return make_response(jsonify({"error": "Not enough data"}), 404)
        
        # Convert the figure to a PNG image
        img_bytes = fig.to_image(format="png")
        
        # Create a file-like object from the bytes
        img_io = io.BytesIO(img_bytes)
        img_io.seek(0)
        
        # Send the file with the appropriate MIME type
        return send_file(img_io, mimetype='image/png')
    
    except Exception as e:
        logger.error(f"Error generating price prediction chart: {e}")
        return make_response(jsonify({"error": str(e)}), 500)

@chart_bp.route('/charts/stock_prediction/<int:product_id>')
def stock_prediction_chart(product_id):
    """Generate stock prediction chart for a product"""
    try:
        fig, predictions = generate_stock_prediction_chart(product_id)
        if fig is None:
            return make_response(jsonify({"error": "Not enough data"}), 404)
        
        # Convert the figure to a PNG image
        img_bytes = fig.to_image(format="png")
        
        # Create a file-like object from the bytes
        img_io = io.BytesIO(img_bytes)
        img_io.seek(0)
        
        # Send the file with the appropriate MIME type
        return send_file(img_io, mimetype='image/png')
    
    except Exception as e:
        logger.error(f"Error generating stock prediction chart: {e}")
        return make_response(jsonify({"error": str(e)}), 500)

@chart_bp.route('/charts/buy_recommendation/<int:product_id>')
def buy_recommendation_chart(product_id):
    """Generate buy recommendation chart for a product"""
    try:
        fig, recommendation = generate_buy_recommendation_chart(product_id)
        if fig is None:
            return make_response(jsonify({"error": "Not enough data"}), 404)
        
        # Convert the figure to a PNG image
        img_bytes = fig.to_image(format="png")
        
        # Create a file-like object from the bytes
        img_io = io.BytesIO(img_bytes)
        img_io.seek(0)
        
        # Send the file with the appropriate MIME type
        return send_file(img_io, mimetype='image/png')
    
    except Exception as e:
        logger.error(f"Error generating buy recommendation chart: {e}")
        return make_response(jsonify({"error": str(e)}), 500)

def generate_price_history_chart(product_id, days=30):
    """
    Generate price history chart for a product
    
    Args:
        product_id: ID of the product
        days: Number of days to include in the chart
        
    Returns:
        Plotly figure object or None if failed
    """
    session = get_session()
    
    try:
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            logger.error(f"Product with ID {product_id} not found")
            return None
        
        # Get price history
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)
        
        price_history = session.query(PriceHistory)\
            .filter(PriceHistory.product_id == product_id)\
            .filter(PriceHistory.timestamp >= start_date)\
            .filter(PriceHistory.timestamp <= end_date)\
            .order_by(PriceHistory.timestamp).all()
        
        if not price_history:
            logger.error(f"No price history found for product ID {product_id}")
            return None
        
        # Prepare data for plotting
        dates = [ph.timestamp for ph in price_history]
        prices = [ph.price for ph in price_history]
        
        # Ensure we have enough data points for a meaningful chart (at least 2)
        if len(dates) < 2:
            logger.warning(f"Not enough price history data points for product ID {product_id}")
            # Add a synthetic second point to allow chart creation
            if len(dates) == 1:
                # Add a second point 1 day later with the same price
                dates.append(dates[0] + datetime.timedelta(days=1))
                prices.append(prices[0])
            else:
                # No data points, can't generate a chart
                return None
        
        # Create DataFrame for plotting
        df = pd.DataFrame({
            'Date': dates,
            'Price': prices
        })
        
        # Create the Plotly figure
        fig = go.Figure()
        
        # Add price line with markers
        fig.add_trace(go.Scatter(
            x=df['Date'], 
            y=df['Price'],
            mode='lines+markers',
            name='Price',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=8)
        ))
        
        # Add min/max price annotations
        min_price = min(prices)
        max_price = max(prices)
        min_index = prices.index(min_price)
        max_index = prices.index(max_price)
        
        fig.add_annotation(
            x=dates[min_index],
            y=min_price,
            text=f"Min: ${min_price:.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="green",
            arrowsize=1,
            arrowwidth=2
        )
        
        fig.add_annotation(
            x=dates[max_index],
            y=max_price,
            text=f"Max: ${max_price:.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="red",
            arrowsize=1,
            arrowwidth=2
        )
        
        # Update layout
        fig.update_layout(
            title=f"Price History for {product.name}",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            template="plotly_white",
            hovermode="x unified",
            width=1000,
            height=500
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        return fig
    
    except Exception as e:
        logger.error(f"Error generating price history chart: {e}")
        return None
    
    finally:
        session.close()

def generate_stock_history_chart(product_id, days=30):
    """
    Generate stock history chart for a product
    
    Args:
        product_id: ID of the product
        days: Number of days to include in the chart
        
    Returns:
        Plotly figure object or None if failed
    """
    session = get_session()
    
    try:
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            logger.error(f"Product with ID {product_id} not found")
            return None
        
        # Get stock history
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)
        
        stock_history = session.query(StockHistory)\
            .filter(StockHistory.product_id == product_id)\
            .filter(StockHistory.timestamp >= start_date)\
            .filter(StockHistory.timestamp <= end_date)\
            .order_by(StockHistory.timestamp).all()
        
        if not stock_history:
            logger.error(f"No stock history found for product ID {product_id}")
            return None
        
        # Prepare data for plotting
        dates = [sh.timestamp for sh in stock_history]
        stocks = [1 if sh.in_stock else 0 for sh in stock_history]
        
        # Ensure we have enough data points for a meaningful chart (at least 2)
        if len(dates) < 2:
            logger.warning(f"Not enough stock history data points for product ID {product_id}")
            # Add a synthetic second point to allow chart creation
            if len(dates) == 1:
                # Add a second point 1 day later with the same stock status
                dates.append(dates[0] + datetime.timedelta(days=1))
                stocks.append(stocks[0])
            else:
                # No data points, can't generate a chart
                return None
        
        # Create DataFrame for plotting
        df = pd.DataFrame({
            'Date': dates,
            'In_Stock': stocks
        })
        
        # Create the Plotly figure
        fig = go.Figure()
        
        # Add stock status as step line
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['In_Stock'],
            mode='lines',
            name='Stock Status',
            line=dict(shape='hv', color='#2ca02c', width=2)
        ))
        
        # Fill the area under the line
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['In_Stock'],
            mode='none',
            fill='tozeroy',
            fillcolor='rgba(44, 160, 44, 0.3)',
            showlegend=False
        ))
        
        # Update layout
        fig.update_layout(
            title=f"Stock History for {product.name}",
            xaxis_title="Date",
            yaxis_title="In Stock",
            template="plotly_white",
            width=1000,
            height=400
        )
        
        # Set Y-axis to show only "In Stock" and "Out of Stock"
        fig.update_yaxes(
            tickvals=[0, 1],
            ticktext=["Out of Stock", "In Stock"]
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        return fig
    
    except Exception as e:
        logger.error(f"Error generating stock history chart: {e}")
        return None
    
    finally:
        session.close()

def generate_price_prediction_chart(product_id, days_ahead=7):
    """
    Generate price prediction chart for a product
    
    Args:
        product_id: ID of the product
        days_ahead: Number of days to predict ahead
        
    Returns:
        tuple: (fig, predictions) or (None, None) if failed
    """
    session = get_session()
    
    try:
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            logger.error(f"Product with ID {product_id} not found")
            return None, None
        
        # Get predictions using our model class
        price_model = PricePredictionModel()
        prediction_result = price_model.predict(product_id, days_ahead)
        
        if not prediction_result:
            logger.warning(f"Failed to generate price predictions for product ID {product_id}. Using historical average instead.")
            
            # Fallback to simple average if model fails
            price_history = session.query(PriceHistory)\
                .filter(PriceHistory.product_id == product_id)\
                .order_by(PriceHistory.timestamp).all()
                
            if not price_history:
                logger.error("No price history available for fallback prediction")
                return None, None
                
            # Calculate average price
            avg_price = sum(ph.price for ph in price_history) / len(price_history)
            
            # Generate constant prediction
            now = datetime.datetime.utcnow()
            future_dates = [now + datetime.timedelta(days=i) for i in range(1, days_ahead + 1)]
            predictions = [(date, avg_price) for date in future_dates]
            std_error = max(ph.price for ph in price_history) - min(ph.price for ph in price_history)
            
            logger.info("Using constant prediction as fallback")
        else:
            predictions, std_error = prediction_result
        
        # Get price history for chart
        price_history = session.query(PriceHistory)\
            .filter(PriceHistory.product_id == product_id)\
            .order_by(PriceHistory.timestamp).all()
            
        historical_dates = [ph.timestamp for ph in price_history]
        historical_prices = [ph.price for ph in price_history]
        
        # Extract prediction data
        prediction_dates, prediction_prices = zip(*predictions)
        
        # Create DataFrames for plotting
        historical_df = pd.DataFrame({
            'Date': historical_dates,
            'Price': historical_prices,
            'Type': 'Historical'
        })
        
        prediction_df = pd.DataFrame({
            'Date': prediction_dates,
            'Price': prediction_prices,
            'Type': 'Predicted',
            'Upper': [p + 1.96 * std_error for p in prediction_prices],
            'Lower': [max(0, p - 1.96 * std_error) for p in prediction_prices]
        })
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Add historical prices
        fig.add_trace(go.Scatter(
            x=historical_df['Date'],
            y=historical_df['Price'],
            mode='lines+markers',
            name='Historical Prices',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # Add predicted prices
        fig.add_trace(go.Scatter(
            x=prediction_df['Date'],
            y=prediction_df['Price'],
            mode='lines+markers',
            name='Predicted Prices',
            line=dict(color='red', width=2, dash='dash')
        ))
        
        # Add confidence interval
        fig.add_trace(go.Scatter(
            x=prediction_df['Date'].tolist() + prediction_df['Date'].tolist()[::-1],
            y=prediction_df['Upper'].tolist() + prediction_df['Lower'].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(255,0,0,0.2)',
            line=dict(color='rgba(255,0,0,0)'),
            hoverinfo='skip',
            showlegend=True,
            name='95% Confidence Interval'
        ))
        
        # Update layout
        fig.update_layout(
            title=f"Price Prediction for Next {days_ahead} Days",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            template="plotly_white",
            hovermode="x unified",
            width=1000,
            height=500
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        return fig, predictions
    
    except Exception as e:
        logger.error(f"Error generating price prediction chart: {e}")
        return None, None
    
    finally:
        session.close()

def generate_stock_prediction_chart(product_id, days_ahead=7):
    """
    Generate stock prediction chart for a product
    
    Args:
        product_id: ID of the product
        days_ahead: Number of days to predict ahead
        
    Returns:
        tuple: (fig, predictions) or (None, None) if failed
    """
    session = get_session()
    
    try:
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            logger.error(f"Product with ID {product_id} not found")
            return None, None
        
        # Get stock predictions using our model class
        stock_model = StockPredictionModel()
        predictions = stock_model.predict(product_id, days_ahead)
        
        if not predictions:
            logger.warning(f"Failed to generate stock predictions for product ID {product_id}. Using historical trend.")
            
            # Fallback: use most recent stock status with declining probability
            stock_history = session.query(StockHistory)\
                .filter(StockHistory.product_id == product_id)\
                .order_by(StockHistory.timestamp.desc()).all()
                
            if not stock_history:
                logger.error("No stock history available for fallback prediction")
                return None, None
                
            # Get most recent stock status
            latest_stock = stock_history[0]
            in_stock = latest_stock.in_stock
            
            # Generate declining probability if in stock, increasing if out of stock
            now = datetime.datetime.utcnow()
            future_dates = [now + datetime.timedelta(days=i) for i in range(1, days_ahead + 1)]
            
            if in_stock:
                # Start with high probability that declines over time
                probs = [max(0.5, 1.0 - (i * 0.05)) for i in range(days_ahead)]
            else:
                # Start with low probability that increases over time
                probs = [min(0.5, 0.0 + (i * 0.05)) for i in range(days_ahead)]
                
            predictions = list(zip(future_dates, probs))
            logger.info("Using trend-based fallback for stock prediction")
        
        # Get stock history for chart
        stock_history = session.query(StockHistory)\
            .filter(StockHistory.product_id == product_id)\
            .order_by(StockHistory.timestamp).all()
            
        historical_dates = [sh.timestamp for sh in stock_history]
        historical_stocks = [1 if sh.in_stock else 0 for sh in stock_history]
        
        # Extract prediction data
        prediction_dates, prediction_probs = zip(*predictions)
        
        # Create DataFrames for plotting
        historical_df = pd.DataFrame({
            'Date': historical_dates,
            'In_Stock': historical_stocks,
            'Type': 'Historical'
        })
        
        prediction_df = pd.DataFrame({
            'Date': prediction_dates,
            'In_Stock': prediction_probs,
            'Type': 'Predicted'
        })
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Add historical stock status
        fig.add_trace(go.Scatter(
            x=historical_df['Date'],
            y=historical_df['In_Stock'],
            mode='lines',
            name='Historical Stock',
            line=dict(shape='hv', color='#2ca02c', width=2)
        ))
        
        # Add predicted stock probability
        fig.add_trace(go.Scatter(
            x=prediction_df['Date'],
            y=prediction_df['In_Stock'],
            mode='lines+markers',
            name='Stock Probability',
            line=dict(color='orange', width=2, dash='dash'),
            marker=dict(size=8)
        ))
        
        # Add a reference line at 0.5 probability
        fig.add_shape(
            type="line",
            x0=prediction_dates[0],
            y0=0.5,
            x1=prediction_dates[-1],
            y1=0.5,
            line=dict(
                color="gray",
                width=1,
                dash="dot",
            )
        )
        
        # Update layout
        fig.update_layout(
            title=f"Stock Availability Prediction for Next {days_ahead} Days",
            xaxis_title="Date",
            yaxis_title="In Stock Probability",
            template="plotly_white",
            hovermode="x unified",
            width=1000,
            height=500
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        # Set Y-axis to range from 0 to 1
        fig.update_yaxes(range=[0, 1])
        
        # Add annotation for the 0.5 threshold
        fig.add_annotation(
            x=prediction_dates[-1],
            y=0.5,
            text="50% Threshold",
            showarrow=False,
            yshift=10,
            bgcolor="rgba(255, 255, 255, 0.8)"
        )
        
        return fig, predictions
    
    except Exception as e:
        logger.error(f"Error generating stock prediction chart: {e}")
        return None, None
    
    finally:
        session.close()

def generate_buy_recommendation_chart(product_id, days_ahead=30):
    """
    Generate buy recommendation chart for a product
    
    Args:
        product_id: ID of the product
        days_ahead: Number of days to look ahead
        
    Returns:
        tuple: (fig, recommendation) or (None, None) if failed
    """
    try:
        session = get_session()
        
        # Get price predictions
        fig, predictions = generate_price_prediction_chart(product_id, days_ahead)
        if fig is None or predictions is None:
            return None, None
        
        # Extract data from predictions for visualization
        prediction_dates, prediction_prices = zip(*predictions)
        
        # Find the day with the lowest predicted price
        min_price_index = prediction_prices.index(min(prediction_prices))
        min_price_date = prediction_dates[min_price_index]
        min_price = prediction_prices[min_price_index]
        
        # Get stock predictions
        stock_fig, stock_predictions = generate_stock_prediction_chart(product_id, days_ahead)
        stock_probs = None
        if stock_predictions:
            _, stock_probs = zip(*stock_predictions)
        
        # Create recommendation dictionary
        recommendation = {
            'best_date': min_price_date,
            'predicted_price': min_price,
            'days_from_now': (min_price_date - datetime.datetime.utcnow()).days,
            'stock_probability': stock_probs[min_price_index] if stock_probs else None
        }
        
        # Get product info
        product = session.query(Product).filter_by(id=product_id).first()
        
        # Create figure for buy recommendation
        fig = go.Figure()
        
        # Add price prediction line
        fig.add_trace(go.Scatter(
            x=prediction_dates,
            y=prediction_prices,
            name='Predicted Price',
            mode='lines+markers',
            line=dict(color='blue', width=2)
        ))
        
        # Add second Y-axis for stock probability if available
        if stock_probs:
            fig.add_trace(go.Scatter(
                x=prediction_dates,
                y=stock_probs,
                name='Stock Probability',
                mode='lines',
                line=dict(color='green', width=2, dash='dash'),
                yaxis='y2'
            ))
        
        # Highlight the recommended buy date
        fig.add_trace(go.Scatter(
            x=[min_price_date],
            y=[min_price],
            mode='markers',
            marker=dict(
                size=15,
                color='red',
                symbol='star'
            ),
            name='Recommended Buy Date'
        ))
        
        # Add annotation for the recommended date
        fig.add_annotation(
            x=min_price_date,
            y=min_price,
            text=f"Best time to buy: ${min_price:.2f}",
            showarrow=True,
            arrowhead=1,
            ax=0,
            ay=-40
        )
        
        # Update layout
        fig.update_layout(
            title=f"Buy Recommendation for {product.name if product else 'Product'}",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            template="plotly_white",
            hovermode="x unified",
            width=1000,
            height=500
        )
        
        # Add second y-axis for stock probability
        if stock_probs:
            fig.update_layout(
                yaxis2=dict(
                    title=dict(text="Stock Probability", font=dict(color='green')),
                    titlefont=dict(color='green'),
                    tickfont=dict(color='green'),
                    overlaying='y',
                    side='right',
                    range=[0, 1]
                )
            )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        return fig, recommendation
    
    except Exception as e:
        logger.error(f"Error generating buy recommendation chart: {e}")
        return None, None
    
    finally:
        if 'session' in locals():
            session.close()