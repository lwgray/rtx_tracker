"""
Best Buy scraper module for RTX 5090 Stock Tracker
"""

import requests
from bs4 import BeautifulSoup
from database.models import Product, PriceHistory, StockHistory
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

def get_headers():
    """Get headers for HTTP requests to mimic a browser"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers',
    }

def scrape_best_buy(session, retailer):
    """
    Scrape RTX 5090 information from Best Buy
    
    Args:
        session: Database session
        retailer: Retailer object
        
    Returns:
        tuple: (product, price, in_stock)
    """
    url = "https://www.bestbuy.com/site/nvidia-geforce-rtx-5090-32gb-gddr7-graphics-card-dark-gun-metal/6614151.p?skuId=6614151"
    logger.info(f"Scraping Best Buy: {url}")
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product details
        product_name = "NVIDIA GeForce RTX 5090 32GB GDDR7 Graphics Card"
        manufacturer = "NVIDIA"
        
        # Check if product exists in database, if not, create it
        product = session.query(Product).filter_by(url=url).first()
        if not product:
            # Extract product description and specifications
            description_div = soup.find('div', {'class': 'product-description'})
            description = description_div.text.strip() if description_div else "No description available"
            
            spec_div = soup.find('div', {'class': 'product-specifications'})
            specifications = spec_div.text.strip() if spec_div else "No specifications available"
            
            # Extract UPC (Best Buy usually has this in their specifications)
            upc = None
            if spec_div:
                upc_row = spec_div.find('tr', string=lambda s: s and 'UPC' in s)
                if upc_row:
                    upc_cell = upc_row.find_next('td')
                    if upc_cell:
                        upc = upc_cell.text.strip()
            
            # If UPC not found in specifications, try the product JSON data
            if not upc:
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'gtin13' in data:
                            upc = data['gtin13']
                            break
                        elif isinstance(data, dict) and 'gtin12' in data:
                            upc = data['gtin12']
                            break
                    except:
                        continue
            
            product = Product(
                retailer_id=retailer.id,
                name=product_name,
                manufacturer=manufacturer,
                upc=upc,  # Add UPC
                url=url,
                description=description,
                specifications=specifications
            )
            session.add(product)
            session.commit()
            logger.info(f"Added new product: {product_name}, UPC: {upc}")
        
        
        # Extract price
        price_elem = soup.select_one('.priceView-customer-price span')
        price = None
        if price_elem:
            price_text = price_elem.text.strip()
            # Remove currency symbol and commas, then convert to float
            price = float(price_text.replace('$', '').replace(',', ''))
        
        # Extract stock status
        add_to_cart_button = soup.find('button', {'data-button-state': 'ADD_TO_CART'})
        in_stock = add_to_cart_button is not None
        
        # Record price and stock status
        if price:
            price_history = PriceHistory(product_id=product.id, price=price)
            session.add(price_history)
        
        stock_history = StockHistory(product_id=product.id, in_stock=in_stock)
        session.add(stock_history)
        session.commit()
        
        logger.info(f"Best Buy: {product_name} - Price: ${price if price else 'N/A'} - In Stock: {in_stock}")
        return product, price, in_stock
    
    except Exception as e:
        logger.error(f"Error scraping Best Buy: {e}")
        return None, None, False