# RTX 5090 Stock Tracker

A Python application that tracks NVIDIA RTX 5090 GPU availability and prices across multiple retailers.

## Features

- Monitors RTX 5090 stock at Best Buy, Newegg, Amazon, and Micro Center
- Alerts via email when products are in stock and under $2,500
- Web dashboard to view current stock and price information
- Price tracking and visualization
- Stock history tracking
- Price prediction using machine learning
- Data export functionality

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and update the configuration
6. Initialize the database: `python reset_database.py`

## Usage

### Run the application

```bash
python run_all.py
```

This will start both the monitoring service and the web dashboard.

### Run the monitoring service only

```bash
python run_all.py --monitor
```

### Run the web dashboard only

```bash
python run_all.py --dashboard
```

### Export data

```bash
python run_all.py --export
```

### Train machine learning models

```bash
python run_all.py --ml-models
```

## Configuration

Edit the `.env` file to configure:

- Database connection
- Email notifications
- Alert thresholds
- Monitoring intervals

## Deployment

The application is configured for deployment on Heroku. To deploy:

1. Create a Heroku app
2. Add PostgreSQL addon
3. Set environment variables
4. Deploy the code

## License

This project is licensed under the MIT License - see the LICENSE file for details.
