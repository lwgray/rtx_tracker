"""
Machine learning predictions for RTX 5090 Stock Tracker
"""

import os
import time
import datetime
import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from database.db import get_session
from database.models import Product, PriceHistory, StockHistory
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)


class StockPredictionModel:
    """Class to train, save, and load Random Forest models for stock prediction"""
    
    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.model = None
        
    def get_model_path(self, product_id):
        """Get path for saving/loading model for a specific product"""
        return os.path.join(self.model_dir, f'stock_model_{product_id}.joblib')
    
    def train(self, product_id, force_retrain=False):
        """Train or load a Random Forest model for stock prediction"""
        model_path = self.get_model_path(product_id)
        
        # Check if model exists and is recent (less than 1 day old)
        if not force_retrain and os.path.exists(model_path):
            model_time = datetime.datetime.fromtimestamp(os.path.getmtime(model_path))
            if datetime.datetime.now() - model_time < datetime.timedelta(days=1):
                self.model = joblib.load(model_path)
                logger.info(f"Loaded existing stock model for product {product_id}")
                return self.model
        
        # Train new model
        session = get_session()
        try:
            # Get stock history
            stock_history = session.query(StockHistory)\
                .filter(StockHistory.product_id == product_id)\
                .order_by(StockHistory.timestamp).all()
            
            if len(stock_history) < 2:  # Reduced from 10 to 2 minimum data points
                logger.warning(f"Insufficient data to train model for product {product_id}, only {len(stock_history)} data points available")
                return None
            
            # Prepare data for modeling
            dates = [sh.timestamp for sh in stock_history]
            stocks = [1 if sh.in_stock else 0 for sh in stock_history]
            
            # Convert dates to numeric feature (days since first record)
            first_date = dates[0]
            X = np.array([(date - first_date).days for date in dates]).reshape(-1, 1)
            y = stocks
            
            # Add more features if available (like day of week, etc.)
            X = np.column_stack([X, [date.weekday() for date in dates]])
            
            # Define hyperparameter grid - simplified for small datasets
            param_grid = {
                'n_estimators': [50, 100],
                'max_depth': [None, 5],
                'min_samples_split': [2]
            }
            
            # For very small datasets, use a simpler model
            if len(X) < 5:
                logger.info(f"Using simpler model due to limited data points ({len(X)})")
                self.model = RandomForestClassifier(n_estimators=50, max_depth=None, random_state=42)
                self.model.fit(X, y)
            
            # For medium datasets, use simple GridSearch
            elif len(X) < 10: 
                logger.info(f"Using simplified grid search due to limited data points ({len(X)})")
                cv_folds = min(3, len(X) // 2)  # Use at most 3-fold CV for smaller datasets
                
                if cv_folds < 2:  # If we can't do CV with the data we have
                    self.model = RandomForestClassifier(n_estimators=50, random_state=42)
                    self.model.fit(X, y)
                else:
                    grid_search = GridSearchCV(
                        RandomForestClassifier(random_state=42),
                        param_grid=param_grid,
                        cv=cv_folds,
                        scoring='accuracy'
                    )
                    grid_search.fit(X, y)
                    self.model = grid_search.best_estimator_
                    logger.info(f"Best parameters: {grid_search.best_params_}")
            
            # For larger datasets, use the full GridSearch
            else:
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20],
                    'min_samples_split': [2, 5, 10]
                }
                
                grid_search = GridSearchCV(
                    RandomForestClassifier(random_state=42),
                    param_grid=param_grid,
                    cv=min(5, len(X) // 2),  # Use at most 5-fold CV
                    scoring='accuracy'
                )
                grid_search.fit(X, y)
                self.model = grid_search.best_estimator_
                logger.info(f"Best parameters: {grid_search.best_params_}")
            
            # Save the model
            joblib.dump(self.model, model_path)
            logger.info(f"Trained and saved new stock model for product {product_id}")
            
            return self.model
            
        except Exception as e:
            logger.error(f"Error training stock model: {e}")
            return None
            
        finally:
            session.close()
    
    def predict(self, product_id, days_ahead=7):
        """Generate stock availability predictions for a product"""
        if self.model is None:
            self.train(product_id)
            
        if self.model is None:
            return None
            
        session = get_session()
        try:
            # Get latest stock history to establish current date
            latest_stock = session.query(StockHistory)\
                .filter(StockHistory.product_id == product_id)\
                .order_by(StockHistory.timestamp.desc())\
                .first()
                
            if not latest_stock:
                return None
                
            # Get first record to establish the baseline for day calculation
            first_stock = session.query(StockHistory)\
                .filter(StockHistory.product_id == product_id)\
                .order_by(StockHistory.timestamp)\
                .first()
                
            first_date = first_stock.timestamp
            last_date = latest_stock.timestamp
            
            # Generate future dates for prediction
            future_days = range(1, days_ahead + 1)
            future_dates = [last_date + datetime.timedelta(days=day) for day in future_days]
            
            # Create features for future dates
            future_days_numeric = [(last_date - first_date).days + day for day in future_days]
            future_weekdays = [date.weekday() for date in future_dates]
            future_X = np.column_stack([
                np.array(future_days_numeric).reshape(-1, 1),
                np.array(future_weekdays).reshape(-1, 1)
            ])
            
            # Make predictions
            predictions = self.model.predict_proba(future_X)[:, 1]  # Probability of being in stock
            
            return list(zip(future_dates, predictions))
            
        except Exception as e:
            logger.error(f"Error generating stock predictions: {e}")
            return None
            
        finally:
            session.close()


class PricePredictionModel:
    """Class to train, save, and load Random Forest models for price prediction"""
    
    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.model = None
        
    def get_model_path(self, product_id):
        """Get path for saving/loading model for a specific product"""
        return os.path.join(self.model_dir, f'price_model_{product_id}.joblib')
    
    def train(self, product_id, force_retrain=False):
        """Train or load a Random Forest model for price prediction"""
        model_path = self.get_model_path(product_id)
        
        # Check if model exists and is recent (less than 1 day old)
        if not force_retrain and os.path.exists(model_path):
            model_time = datetime.datetime.fromtimestamp(os.path.getmtime(model_path))
            if datetime.datetime.now() - model_time < datetime.timedelta(days=1):
                self.model = joblib.load(model_path)
                logger.info(f"Loaded existing price model for product {product_id}")
                return self.model
        
        # Train new model
        session = get_session()
        try:
            # Get price history
            price_history = session.query(PriceHistory)\
                .filter(PriceHistory.product_id == product_id)\
                .order_by(PriceHistory.timestamp).all()
            
            if len(price_history) < 2:  # Reduced from 10 to 2 minimum data points
                logger.warning(f"Insufficient data to train model for product {product_id}, only {len(price_history)} data points available")
                return None
            
            # Prepare data for modeling
            dates = [ph.timestamp for ph in price_history]
            prices = [ph.price for ph in price_history]
            
            # Convert dates to numeric feature (days since first record)
            first_date = dates[0]
            X = np.array([(date - first_date).days for date in dates]).reshape(-1, 1)
            y = prices
            
            # Add more features if available (like day of week, etc.)
            X = np.column_stack([X, [date.weekday() for date in dates]])
            
            # Define hyperparameter grid - simplified for small datasets
            param_grid = {
                'n_estimators': [50, 100],
                'max_depth': [None, 5],
                'min_samples_split': [2]
            }
            
            # For very small datasets, use a simpler model
            if len(X) < 5:
                logger.info(f"Using simpler model due to limited data points ({len(X)})")
                self.model = RandomForestRegressor(n_estimators=50, max_depth=None, random_state=42)
                self.model.fit(X, y)
            
            # For medium datasets, use simple GridSearch
            elif len(X) < 10:
                logger.info(f"Using simplified grid search due to limited data points ({len(X)})")
                cv_folds = min(3, len(X) // 2)  # Use at most 3-fold CV for smaller datasets
                
                if cv_folds < 2:  # If we can't do CV with the data we have
                    self.model = RandomForestRegressor(n_estimators=50, random_state=42)
                    self.model.fit(X, y)
                else:
                    grid_search = GridSearchCV(
                        RandomForestRegressor(random_state=42),
                        param_grid=param_grid,
                        cv=cv_folds,
                        scoring='neg_mean_squared_error'
                    )
                    grid_search.fit(X, y)
                    self.model = grid_search.best_estimator_
                    logger.info(f"Best parameters: {grid_search.best_params_}")
            
            # For larger datasets, use the full GridSearch
            else:
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20],
                    'min_samples_split': [2, 5, 10]
                }
                
                grid_search = GridSearchCV(
                    RandomForestRegressor(random_state=42),
                    param_grid=param_grid,
                    cv=min(5, len(X) // 2),  # Use at most 5-fold CV
                    scoring='neg_mean_squared_error'
                )
                grid_search.fit(X, y)
                self.model = grid_search.best_estimator_
                logger.info(f"Best parameters: {grid_search.best_params_}")
            
            # Save the model
            joblib.dump(self.model, model_path)
            logger.info(f"Trained and saved new price model for product {product_id}")
            
            return self.model
            
        except Exception as e:
            logger.error(f"Error training price model: {e}")
            return None
            
        finally:
            session.close()
    
    def predict(self, product_id, days_ahead=7):
        """Generate price predictions for a product"""
        if self.model is None:
            self.train(product_id)
            
        if self.model is None:
            return None
            
        session = get_session()
        try:
            # Get latest price history to establish current date
            latest_price = session.query(PriceHistory)\
                .filter(PriceHistory.product_id == product_id)\
                .order_by(PriceHistory.timestamp.desc())\
                .first()
                
            if not latest_price:
                return None
                
            # Get first record to establish the baseline for day calculation
            first_price = session.query(PriceHistory)\
                .filter(PriceHistory.product_id == product_id)\
                .order_by(PriceHistory.timestamp)\
                .first()
                
            first_date = first_price.timestamp
            last_date = latest_price.timestamp
            
            # Generate future dates for prediction
            future_days = range(1, days_ahead + 1)
            future_dates = [last_date + datetime.timedelta(days=day) for day in future_days]
            
            # Create features for future dates
            future_days_numeric = [(last_date - first_date).days + day for day in future_days]
            future_weekdays = [date.weekday() for date in future_dates]
            future_X = np.column_stack([
                np.array(future_days_numeric).reshape(-1, 1),
                np.array(future_weekdays).reshape(-1, 1)
            ])
            
            # Make predictions
            predictions = self.model.predict(future_X)
            
            # Calculate error for confidence interval
            price_history = session.query(PriceHistory)\
                .filter(PriceHistory.product_id == product_id)\
                .order_by(PriceHistory.timestamp).all()
                
            dates = [ph.timestamp for ph in price_history]
            prices = [ph.price for ph in price_history]
            
            # Convert dates to numeric feature (days since first record)
            X = np.array([(date - first_date).days for date in dates]).reshape(-1, 1)
            X = np.column_stack([X, [date.weekday() for date in dates]])
            y = prices
            
            # Calculate standard error more safely
            try:
                y_pred = self.model.predict(X)
                mse = np.mean((y - y_pred) ** 2)
                std_error = np.sqrt(mse)
            except Exception as e:
                logger.warning(f"Error calculating prediction error: {e}. Using default error value.")
                std_error = (max(y) - min(y)) * 0.1  # Use 10% of range as fallback
            
            return list(zip(future_dates, predictions)), std_error
            
        except Exception as e:
            logger.error(f"Error generating price predictions: {e}")
            return None
            
        finally:
            session.close()


def predict_price_trend(product_id, days_ahead=7):
    """
    Predict price trend for a product using machine learning
    
    Args:
        product_id: ID of the product
        days_ahead: Number of days to predict into the future
        
    Returns:
        tuple: (chart_filename, predictions) or None if failed
    """
    session = get_session()
    
    try:
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            logger.error(f"Product with ID {product_id} not found")
            return None
        
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
                return None
                
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
            'Upper': np.array(prediction_prices) + 1.96 * std_error,
            'Lower': np.array(prediction_prices) - 1.96 * std_error
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
        
        # Ensure static directory exists
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img')
        os.makedirs(static_dir, exist_ok=True)
        
        # Save the plot as a PNG file
        filename = f"price_prediction_{product_id}_{int(time.time())}.png"
        filepath = os.path.join(static_dir, filename)
        fig.write_image(filepath)
        
        # Generate an HTML version for interactive viewing
        html_filename = f"price_prediction_{product_id}_{int(time.time())}.html"
        html_filepath = os.path.join(static_dir, html_filename)
        fig.write_html(html_filepath)
        
        logger.info(f"Price prediction generated for product ID {product_id} and saved as {filename}")
        return filename, predictions
    
    except Exception as e:
        logger.error(f"Error predicting price trend: {e}")
        return None
    
    finally:
        session.close()


def predict_stock_availability(product_id, days_ahead=7):
    """
    Predict stock availability for a product
    
    Args:
        product_id: ID of the product
        days_ahead: Number of days to predict into the future
        
    Returns:
        tuple: (chart_filename, predictions) or None if failed
    """
    session = get_session()
    
    try:
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            logger.error(f"Product with ID {product_id} not found")
            return None
        
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
                return None
                
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
        
        # Ensure static directory exists
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img')
        os.makedirs(static_dir, exist_ok=True)
        
        # Save the plot as a PNG file
        filename = f"stock_prediction_{product_id}_{int(time.time())}.png"
        filepath = os.path.join(static_dir, filename)
        fig.write_image(filepath)
        
        # Generate an HTML version for interactive viewing
        html_filename = f"stock_prediction_{product_id}_{int(time.time())}.html"
        html_filepath = os.path.join(static_dir, html_filename)
        fig.write_html(html_filepath)
        
        logger.info(f"Stock prediction generated for product ID {product_id} and saved as {filename}")
        return filename, predictions
    
    except Exception as e:
        logger.error(f"Error predicting stock availability: {e}")
        return None
    
    finally:
        session.close()


def recommend_best_time_to_buy(product_id, days_ahead=30):
    """
    Recommend the best time to buy a product based on price predictions
    
    Args:
        product_id: ID of the product
        days_ahead: Number of days to look ahead
        
    Returns:
        dict: Recommendation details or None if failed
    """
    try:
        # Get price predictions
        prediction_result = predict_price_trend(product_id, days_ahead)
        if not prediction_result:
            return None
        
        _, predictions = prediction_result
        
        # Find the day with the lowest predicted price
        prediction_dates, prediction_prices = zip(*predictions)
        min_price_index = prediction_prices.index(min(prediction_prices))
        min_price_date = prediction_dates[min_price_index]
        min_price = prediction_prices[min_price_index]
        
        # Get stock predictions
        stock_prediction_result = predict_stock_availability(product_id, days_ahead)
        stock_availability = None
        
        if stock_prediction_result:
            _, stock_predictions = stock_prediction_result
            _, stock_probs = zip(*stock_predictions)
            stock_availability = stock_probs[min_price_index]
        
        # Create recommendation dictionary
        recommendation = {
            'best_date': min_price_date,
            'predicted_price': min_price,
            'days_from_now': (min_price_date - datetime.datetime.utcnow()).days,
            'stock_probability': stock_availability
        }
        
        # Create a visual recommendation chart
        session = get_session()
        product = session.query(Product).filter_by(id=product_id).first()
        session.close()
        
        # Extract data from predictions for visualization
        dates = [date for date, _ in predictions]
        prices = [price for _, price in predictions]
        
        # Stock probabilities if available
        stock_probs = None
        if stock_prediction_result:
            _, stock_predictions = stock_prediction_result
            stock_probs = [prob for _, prob in stock_predictions]
        
        # Create figure
        fig = go.Figure()
        
        # Add price prediction line
        fig.add_trace(go.Scatter(
            x=dates,
            y=prices,
            name='Predicted Price',
            mode='lines+markers',
            line=dict(color='blue', width=2)
        ))
        
        # Add second Y-axis for stock probability if available
        if stock_probs:
            fig.add_trace(go.Scatter(
                x=dates,
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
                    title="Stock Probability",
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
        
        # Ensure static directory exists
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img')
        os.makedirs(static_dir, exist_ok=True)
        
        # Save the recommendation chart
        filename = f"buy_recommendation_{product_id}_{int(time.time())}.png"
        filepath = os.path.join(static_dir, filename)
        fig.write_image(filepath)
        
        # Generate an HTML version for interactive viewing
        html_filename = f"buy_recommendation_{product_id}_{int(time.time())}.html"
        html_filepath = os.path.join(static_dir, html_filename)
        fig.write_html(html_filepath)
        
        # Add the chart to the recommendation
        recommendation['chart_filename'] = filename
        recommendation['html_chart_filename'] = html_filename
        
        logger.info(f"Best time to buy recommendation for product ID {product_id}: {min_price_date.strftime('%Y-%m-%d')}")
        return recommendation
    
    except Exception as e:
        logger.error(f"Error generating best time to buy recommendation: {e}")
        return None