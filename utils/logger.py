"""
Logging utilities for RTX 5090 Stock Tracker
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def setup_logger():
    """
    Set up the main application logger
    
    Returns:
        Logger: Configured logger instance
    """
    logger = logging.getLogger("RTX_Tracker")
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers = []
    
    # Create file handler for logging to a file
    file_handler = RotatingFileHandler(
        'logs/rtx_tracker.log',
        maxBytes=10485760,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Create console handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create a formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name=None):
    """
    Get a module-specific logger
    
    Args:
        name: Name of the module (usually __name__)
        
    Returns:
        Logger: Module-specific logger instance
    """
    if name is None:
        return logging.getLogger("RTX_Tracker")
    
    logger = logging.getLogger(name)
    
    # If this is the first time this logger is requested, configure it
    if not logger.handlers and not logger.parent.handlers:
        setup_logger()
    
    return logger