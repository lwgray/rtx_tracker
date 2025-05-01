"""
Application configuration for RTX 5090 Stock Tracker
"""

import os

def load_config():
    """
    Load configuration from environment variables
    
    Returns:
        dict: Configuration parameters
    """
    config = {
        # Alert settings
        'ALERT_PRICE_THRESHOLD': float(os.getenv('ALERT_PRICE_THRESHOLD', 2500)),
        
        # Database settings
        'DATABASE_URL': os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/rtx_tracker'),
        
        # Email settings
        'SMTP_SERVER': os.getenv('SMTP_SERVER', ''),
        'SMTP_PORT': int(os.getenv('SMTP_PORT', 587)),
        'SMTP_USERNAME': os.getenv('SMTP_USERNAME', ''),
        'SMTP_PASSWORD': os.getenv('SMTP_PASSWORD', ''),
        'FROM_EMAIL': os.getenv('FROM_EMAIL', ''),
        'TO_EMAIL': os.getenv('TO_EMAIL', ''),
        
        # Monitoring settings
        'MONITORING_INTERVAL': int(os.getenv('MONITORING_INTERVAL', 60)),  # minutes
        
        # Web dashboard settings
        'PORT': int(os.getenv('PORT', 5000)),
        'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
        
        # Product URLs
        'URLS': {
            'BEST_BUY': 'https://www.bestbuy.com/site/nvidia-geforce-rtx-5090-32gb-gddr7-graphics-card-dark-gun-metal/6614151.p?skuId=6614151',
            'NEWEGG': 'https://www.newegg.com/p/pl?d=rtx+5090',
            'AMAZON': 'https://www.amazon.com/s?k=rtx+5090',
            'MICRO_CENTER': 'https://www.microcenter.com/search/search_results.aspx?N=&cat=&Ntt=rtx+5090',
            'BH_PHOTO': 'https://www.bhphotovideo.com/c/search?q=rtx%205090'
        }
    }
    
    return config