#!/usr/bin/env python3
"""
Cleanup script to remove debug HTML files
"""

import os
import glob
import shutil
from utils.logger import setup_logger

def cleanup_static_img_html():
    """Remove HTML files from static/img directory"""
    logger = setup_logger()
    
    # Path to static/img directory
    static_img_dir = os.path.join(os.path.dirname(__file__), 'static', 'img')
    
    # Pattern for HTML files
    html_pattern = os.path.join(static_img_dir, '*.html')
    
    # Count of files removed
    count = 0
    
    # Find and remove HTML files
    for html_file in glob.glob(html_pattern):
        try:
            os.remove(html_file)
            count += 1
        except Exception as e:
            logger.error(f"Error removing file {html_file}: {e}")
    
    logger.info(f"Removed {count} HTML files from static/img directory")
    return count

def cleanup_logs_debug_html():
    """Remove HTML files from logs/debug directory"""
    logger = setup_logger()
    
    # Path to logs/debug directory
    logs_debug_dir = os.path.join(os.path.dirname(__file__), 'logs', 'debug')
    
    if not os.path.exists(logs_debug_dir):
        logger.info("logs/debug directory doesn't exist, nothing to clean up")
        return 0
    
    # Pattern for HTML files
    html_pattern = os.path.join(logs_debug_dir, '*.html')
    
    # Count of files removed
    count = 0
    
    # Find and remove HTML files
    for html_file in glob.glob(html_pattern):
        try:
            os.remove(html_file)
            count += 1
        except Exception as e:
            logger.error(f"Error removing file {html_file}: {e}")
    
    logger.info(f"Removed {count} HTML files from logs/debug directory")
    return count

def main():
    """Main function"""
    logger = setup_logger()
    logger.info("Starting cleanup of debug HTML files")
    
    # Clean up static/img HTML files
    static_count = cleanup_static_img_html()
    
    # Clean up logs/debug HTML files
    logs_count = cleanup_logs_debug_html()
    
    total = static_count + logs_count
    logger.info(f"Cleanup complete. Removed {total} HTML files in total")
    print(f"Cleanup complete. Removed {total} HTML files in total")

if __name__ == "__main__":
    main()