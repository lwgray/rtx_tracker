I'll create a comprehensive, updated README file for your RTX 5090 Stock Tracker application that includes all the new features and implementation details.

# RTX 5090 Stock Tracker

A powerful Python application that tracks NVIDIA RTX 5090 GPU availability and prices across multiple retailers with machine learning-powered predictions.

## Features

- **Automated Stock Monitoring**: Checks availability and prices at Best Buy, Newegg, Amazon, NVIDIA, Micro Center, and B&H Photo
- **Real-time Alerts**: Receive email notifications when RTX 5090s are in stock and priced below $2,500
- **Interactive Dashboard**: Visualize price/stock trends and predictions with Dash-powered analytics
- **Machine Learning Predictions**: 
  - Price trend forecasting using Random Forest models
  - Stock availability predictions with confidence intervals
  - Smart "best time to buy" recommendations
- **Model Persistence**: Trained models are saved and reused to avoid unnecessary retraining
- **Data Collection**: Captures comprehensive product details, prices, and stock information
- **Historical Analysis**: Maintains a database of price and stock history for trend analysis
- **Data Export**: Export collected data to CSV files for external analysis

## Requirements

- Python 3.9 or higher
- PostgreSQL database
- Dependencies listed in `requirements.txt`

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/rtx-5090-tracker.git
   cd rtx-5090-tracker
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a PostgreSQL database:
   ```
   createdb rtx_tracker
   ```

4. Create a `.env` file with the following variables:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/rtx_tracker
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-email-password
   FROM_EMAIL=your-email@gmail.com
   TO_EMAIL=your-email@gmail.com
   ```

## Usage

### Interactive Dashboard

Run the interactive Dash dashboard:
```
python app.py --dashboard
```

The dashboard is available at:
- Flask Interface: http://localhost:5000/
- Dash Analytics Dashboard: http://localhost:5000/dashboard/

### Stock Monitoring

Run the stock monitoring service:
```
python app.py --monitor
```

### Train Machine Learning Models

Train or retrain the machine learning models:
```
python app.py --ml-models
```

### Data Export

Export data to CSV files:
```
python app.py --export
```

You can specify the number of days to include:
```
python app.py --export --days 60
```

### Running All Services

Run both the monitoring service and dashboard:
```
python app.py
```

## Machine Learning Components

The application uses Random Forest algorithms for two key prediction tasks:

1. **Price Trend Forecasting**: Predicts future RTX 5090 prices based on historical data
   - Includes 95% confidence intervals
   - Model is trained with hyperparameter optimization
   - Additional features like day-of-week are incorporated

2. **Stock Availability Prediction**: Forecasts the probability of products being in stock
   - Uses classification with probability outputs
   - Model persistence avoids unnecessary retraining
   - Includes visualization of stock probability over time

3. **Buying Recommendations**: Combines price and stock predictions to recommend the optimal purchase time

All models are automatically persisted to disk and only retrained when necessary, improving application performance.

## Heroku Deployment

1. Create a Heroku account and install the Heroku CLI.

2. Create a new Heroku app:
   ```
   heroku create rtx-tracker
   ```

3. Add a PostgreSQL database:
   ```
   heroku addons:create heroku-postgresql:hobby-dev
   ```

4. Set environment variables:
   ```
   heroku config:set SMTP_SERVER=smtp.gmail.com
   heroku config:set SMTP_PORT=587
   heroku config:set SMTP_USERNAME=your-email@gmail.com
   heroku config:set SMTP_PASSWORD=your-email-password
   heroku config:set FROM_EMAIL=your-email@gmail.com
   heroku config:set TO_EMAIL=your-email@gmail.com
   ```

5. Deploy to Heroku:
   ```
   git push heroku main
   ```

6. Scale the application:
   ```
   heroku ps:scale web=1 worker=1
   ```

## Project Structure

- `app.py`: Main application file with command-line interface
- `dashboard.py`: Dash-powered interactive analytics dashboard
- `services/`
  - `monitoring.py`: Stock monitoring and retailer scrapers
  - `predictions.py`: Machine learning models and prediction logic
  - `analysis.py`: Data analysis and visualization utilities
  - `alerts.py`: Email notification system
- `database/`
  - `db.py`: Database connection utilities
  - `models.py`: SQLAlchemy models
- `web/`
  - `dashboard.py`: Flask web interface
- `templates/`: HTML templates for the web interface
- `static/`: CSS, JavaScript, and image files
- `models/`: Directory for saved machine learning models

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

MIT

## Disclaimer

This application is for educational purposes only. Please use responsibly and respect the terms of service of the retailers being monitored.