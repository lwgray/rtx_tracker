#!/usr/bin/env python3
"""
Cleanup script to remove all PNG files from the repository
and ensure they're properly excluded from git tracking.
"""

import os
import glob
from utils.logger import setup_logger

# Set up logging
logger = setup_logger()

def remove_png_files():
    """
    Find and remove all PNG files from the static/img directory
    """
    # Define the image directory path
    img_dir = os.path.join(os.path.dirname(__file__), 'static', 'img')
    
    if not os.path.exists(img_dir):
        logger.warning(f"Image directory not found: {img_dir}")
        return 0
    
    # Get all PNG files
    png_pattern = os.path.join(img_dir, '*.png')
    png_files = glob.glob(png_pattern)
    
    removed_count = 0
    for file_path in png_files:
        try:
            os.remove(file_path)
            removed_count += 1
            logger.info(f"Removed PNG file: {file_path}")
        except Exception as e:
            logger.error(f"Error removing file {file_path}: {e}")
    
    logger.info(f"Removed {removed_count} PNG files from {img_dir}")
    return removed_count

if __name__ == "__main__":
    # Remove all PNG files
    removed_count = remove_png_files()
    
    print(f"Removed {removed_count} PNG files from static/img directory")
    print("Make sure to commit these changes with:")
    print("git add .gitignore")
    print("git add -u static/img/")
    print("git commit -m \"Remove all static PNG files from repository\"")
    print("git push origin main")