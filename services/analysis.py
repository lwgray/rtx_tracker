"""
Data analysis and visualization for RTX 5090 Stock Tracker
"""

import time
import datetime
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database.db import get_session
from database.models import Product, PriceHistory, StockHistory
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

def generate_price_history_chart(product_id, days=30):
    """
    Generate price history chart for a product
    
    Args:
        product_id: ID of the product
        days: Number of days to include in the chart
        
    Returns:
        str: Filename of the generated chart or None if failed
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
        
        # Ensure static directory exists
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img')
        os.makedirs(static_dir, exist_ok=True)
        
        # Save the plot as a PNG file
        filename = f"price_history_{product_id}_{int(time.time())}.png"
        filepath = os.path.join(static_dir, filename)
        fig.write_image(filepath)
        
        # Generate an HTML version for interactive viewing
        timestamp = int(time.time())
        html_filename = f"price_history_{product_id}_{timestamp}.html"
        html_filepath = os.path.join(static_dir, html_filename)
        
        # Ensure we use the same timestamp for both files to keep them in sync
        filename = f"price_history_{product_id}_{timestamp}.png"
        filepath = os.path.join(static_dir, filename)
        
        try:
            # Save both formats
            fig.write_image(filepath)
            fig.write_html(html_filepath)
            
            logger.info(f"Price history chart generated for {product.name} and saved as {filename} and {html_filename}")
            # Add a flag to indicate that HTML is available
            return filename
        except Exception as e:
            logger.error(f"Error saving chart files: {e}")
            # Try to save just the PNG if HTML fails
            try:
                fig.write_image(filepath)
                logger.info(f"Fallback: Only PNG version saved as {filename}")
                return filename
            except:
                logger.error("Failed to save any chart format")
                return None
    
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
        str: Filename of the generated chart or None if failed
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
        
        # Ensure static directory exists
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img')
        os.makedirs(static_dir, exist_ok=True)
        
        # Save the plot as a PNG file
        filename = f"stock_history_{product_id}_{int(time.time())}.png"
        filepath = os.path.join(static_dir, filename)
        fig.write_image(filepath)
        
        # Generate an HTML version for interactive viewing
        timestamp = int(time.time())
        html_filename = f"stock_history_{product_id}_{timestamp}.html"
        html_filepath = os.path.join(static_dir, html_filename)
        
        # Ensure we use the same timestamp for both files to keep them in sync
        filename = f"stock_history_{product_id}_{timestamp}.png"
        filepath = os.path.join(static_dir, filename)
        
        try:
            # Save both formats
            fig.write_image(filepath)
            fig.write_html(html_filepath)
            
            logger.info(f"Stock history chart generated for {product.name} and saved as {filename} and {html_filename}")
            # Add a flag to indicate that HTML is available
            return filename
        except Exception as e:
            logger.error(f"Error saving chart files: {e}")
            # Try to save just the PNG if HTML fails
            try:
                fig.write_image(filepath)
                logger.info(f"Fallback: Only PNG version saved as {filename}")
                return filename
            except:
                logger.error("Failed to save any chart format")
                return None
    
    except Exception as e:
        logger.error(f"Error generating stock history chart: {e}")
        return None
    
    finally:
        session.close()

def export_data_to_csv(days=30):
    """
    Export recent data to CSV files for analysis
    
    Args:
        days: Number of days of data to export
        
    Returns:
        bool: True if export was successful, False otherwise
    """

    session = get_session()
    
    try:
        # Calculate date range
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Export product data
        products = session.query(Product).all()
        product_data = [{
            'id': p.id,
            'retailer': p.retailer.name,
            'name': p.name,
            'manufacturer': p.manufacturer,
            'url': p.url
        } for p in products]
        
        products_df = pd.DataFrame(product_data)
        products_df.to_csv('export_products.csv', index=False)
        
        # Export price history
        price_history = session.query(PriceHistory)\
            .filter(PriceHistory.timestamp >= start_date)\
            .order_by(PriceHistory.timestamp).all()
        
        price_data = [{
            'product_id': ph.product_id,
            'price': ph.price,
            'timestamp': ph.timestamp
        } for ph in price_history]
        
        price_df = pd.DataFrame(price_data)
        price_df.to_csv('export_price_history.csv', index=False)
        
        # Export stock history
        stock_history = session.query(StockHistory)\
            .filter(StockHistory.timestamp >= start_date)\
            .order_by(StockHistory.timestamp).all()
        
        stock_data = [{
            'product_id': sh.product_id,
            'in_stock': sh.in_stock,
            'timestamp': sh.timestamp
        } for sh in stock_history]
        
        stock_df = pd.DataFrame(stock_data)
        stock_df.to_csv('export_stock_history.csv', index=False)
        
        logger.info(f"Data exported to CSV files for the last {days} days")
        return True
    
    except Exception as e:
        logger.error(f"Error exporting data to CSV: {e}")
        return False
    
    finally:
        session.close()