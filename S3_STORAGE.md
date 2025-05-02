# RTX Tracker S3 Storage Guide

This document explains how the RTX Tracker application handles image storage and chart generation.

## Overview

RTX Tracker can generate and store charts in two ways:

1. **Dynamic On-Demand Generation (default)**: Charts are generated dynamically when requested and served directly without persistent storage.
2. **S3 Storage (optional)**: Charts can be stored in Amazon S3 for longer-term persistence.

## Dynamic Chart Generation

The default mode generates charts on-demand via the `/charts/` API endpoints:

- `/charts/price_history/<product_id>` - Shows price history for a product
- `/charts/stock_history/<product_id>` - Shows stock availability history
- `/charts/price_prediction/<product_id>` - Shows price predictions
- `/charts/stock_prediction/<product_id>` - Shows stock availability predictions
- `/charts/buy_recommendation/<product_id>` - Shows buying recommendation

These endpoints:
1. Generate Plotly charts in memory based on database data
2. Convert charts to PNG format in memory
3. Stream the image directly to the client
4. Don't store any files on disk

## Configuring S3 Storage

To enable S3 storage:

1. Add the following variables to your `.env` file:

```
# S3 settings
S3_BUCKET_NAME=your-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

2. Create an S3 bucket with public read access
3. Configure CORS on your S3 bucket to allow access from your domain

## How S3 Storage Works

When S3 storage is enabled:

1. Charts are first generated in memory using Plotly
2. They are uploaded directly to S3 using the `s3_storage.upload_plotly_figure()` method
3. The URL to the S3-hosted image is returned
4. Local temporary files are cleaned up

## File Cleanup

RTX Tracker includes automatic cleanup to prevent disk space issues:

1. **Local Cleanup**: The `utils/cleanup.py` script removes old chart files from the `static/img` directory
2. **S3 Cleanup**: Old files in S3 are removed after a configurable retention period
3. **Scheduled Cleanup**: When the application starts, it schedules daily cleanup at 3:00 AM

## Storage Strategy

The application follows this strategy:

1. If S3 is configured, charts are preferentially stored in S3
2. If S3 is not available or fails, charts are stored locally as a fallback
3. On-demand chart generation is always available regardless of S3 configuration

## Running the Cleanup Tools

You can manually run the cleanup tools to remove temporary files:

```bash
# Remove all local PNG files
python cleanup_png_files.py

# Verify S3 configuration and update .gitignore
python utils/ensure_s3_storage.py
```

## .gitignore Configuration

The repository is configured to exclude generated chart files from version control:

```
# Generated files
*.log
logs/debug/
logs/*.log
static/img/*.png
static/img/*.html
models/*.joblib
```

This ensures that temporary files don't bloat the Git repository.