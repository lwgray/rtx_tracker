# Deploying RTX Tracker to Heroku

This guide provides instructions for deploying the RTX 5090 Stock Tracker application to Heroku.

> **S3 Storage Recommendation**: For production deployment, it's highly recommended to set up an S3 bucket for storing chart images to avoid filling up your Heroku dyno's ephemeral storage. See the README.md for S3 configuration instructions.

## Prerequisites

1. A Heroku account
2. Heroku CLI installed on your local machine
3. Git installed on your local machine

## Deployment Steps

### 1. Create a new Heroku app

```bash
# Login to Heroku
heroku login

# Create a new Heroku app
heroku create your-rtx-tracker

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:mini
```

### 2. Configure environment variables

```bash
# Set the required environment variables
heroku config:set SECRET_KEY=$(openssl rand -hex 24)
heroku config:set SMTP_SERVER=smtp.gmail.com
heroku config:set SMTP_PORT=587
heroku config:set SMTP_USERNAME=your-email@gmail.com
heroku config:set SMTP_PASSWORD=your-email-app-password
heroku config:set FROM_EMAIL=your-email@gmail.com
heroku config:set TO_EMAIL=your-email@gmail.com
heroku config:set ALERT_PRICE_THRESHOLD=2500
heroku config:set MONITORING_INTERVAL=60
heroku config:set DEBUG=False

# Optional: Set S3 configuration (highly recommended for production)
heroku config:set S3_BUCKET_NAME=your-bucket-name
heroku config:set AWS_REGION=us-east-1
heroku config:set AWS_ACCESS_KEY_ID=your-access-key
heroku config:set AWS_SECRET_ACCESS_KEY=your-secret-key
```

### 3. Add Selenium buildpack for Heroku

The application uses Selenium for web scraping. Heroku requires a special buildpack to run Chrome in headless mode:

```bash
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-chrome-for-testing
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-chromedriver
```

### 4. Configure environment variables for Selenium

```bash
heroku config:set CHROMEDRIVER_PATH=/app/.chromedriver/bin/chromedriver
heroku config:set GOOGLE_CHROME_BIN=/app/.apt/usr/bin/google-chrome
```

### 5. Deploy to Heroku

```bash
# Push to Heroku
git push heroku main

# Initialize the database
heroku run python reset_database.py
```

### 6. Scale workers

The application uses separate processes for the web interface and monitoring:

```bash
# Scale web and worker dynos
heroku ps:scale web=1 worker=1
```

### 7. Open the application

```bash
heroku open
```

## Monitoring Logs

To monitor application logs:

```bash
heroku logs --tail
```

## Database Management

To access the PostgreSQL database:

```bash
heroku pg:psql
```

## Troubleshooting

### Selenium issues

If you encounter issues with Selenium, check the logs and ensure the ChromeDriver version matches the Chrome version on Heroku.

### Database connections

Heroku provides DATABASE_URL in the format `postgres://` but SQLAlchemy requires `postgresql://`. The application's database connection code handles this automatically.