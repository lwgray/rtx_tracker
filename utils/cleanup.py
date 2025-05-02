"""
Cleanup utilities for the RTX 5090 Stock Tracker
"""

import os
import glob
import datetime
import shutil
from utils.logger import get_logger
from utils.s3_storage import s3_storage

# Get logger
logger = get_logger(__name__)

def cleanup_old_files(days_old=7):
    """
    Clean up old image files from static/img directory and/or S3
    
    Args:
        days_old: Delete files older than this many days
        
    Returns:
        tuple: (local_count, s3_count) - Number of files deleted locally and from S3
    """
    local_count = cleanup_local_files(days_old)
    s3_count = cleanup_s3_files(days_old)
    
    return local_count, s3_count

def cleanup_local_files(days_old=7):
    """
    Clean up old image files from static/img directory
    
    Args:
        days_old: Delete files older than this many days
        
    Returns:
        int: Number of files deleted
    """
    deleted_count = 0
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days_old)
    
    # Define the image directory path
    img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img')
    
    if not os.path.exists(img_dir):
        logger.warning(f"Image directory not found: {img_dir}")
        return 0
    
    # Get all PNG and HTML files
    file_patterns = [
        os.path.join(img_dir, '*.png'),
        os.path.join(img_dir, '*.html')
    ]
    
    for pattern in file_patterns:
        for file_path in glob.glob(pattern):
            try:
                # Get file modification time
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # If file is older than cutoff, delete it
                if mod_time < cutoff_time:
                    # Check if it's a chart file we want to clean up
                    filename = os.path.basename(file_path)
                    if any(filename.startswith(prefix) for prefix in [
                        'price_history_', 'stock_history_', 'price_prediction_', 
                        'stock_prediction_', 'buy_recommendation_'
                    ]):
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning up file {file_path}: {e}")
    
    logger.info(f"Cleaned up {deleted_count} old files from local storage")
    return deleted_count

def cleanup_s3_files(days_old=7):
    """
    Clean up old image files from S3
    
    Args:
        days_old: Delete files older than this many days
        
    Returns:
        int: Number of files deleted
    """
    if not s3_storage.is_enabled():
        logger.info("S3 storage not enabled, skipping S3 cleanup")
        return 0
    
    # Prefixes to clean up
    prefixes = [
        'price_history_', 
        'stock_history_', 
        'price_prediction_', 
        'stock_prediction_', 
        'buy_recommendation_'
    ]
    
    total_deleted = 0
    
    # Clean up files with each prefix
    for prefix in prefixes:
        deleted = s3_storage.cleanup_old_files(prefix=prefix, days=days_old)
        total_deleted += deleted
    
    logger.info(f"Cleaned up {total_deleted} old files from S3 storage")
    return total_deleted

def schedule_cleanup():
    """
    Schedule regular cleanup of old files
    """
    import schedule
    
    # Run cleanup once a day
    schedule.every().day.at("03:00").do(cleanup_old_files)
    logger.info("Scheduled daily cleanup of old files at 3:00 AM")
    
    return True