"""
NVIDIA scraper module for RTX 5090 Stock Tracker
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

def scrape_nvidia(session, retailer):
    """
    Scrape RTX 5090 information from NVIDIA's official store
    
    Args:
        session: Database session
        retailer: Retailer object
        
    Returns:
        list: List of (product, price, in_stock) tuples
    """
    url = "https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/"
    logger.info(f"Scraping NVIDIA: {url}")
    
    results = []
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # NVIDIA usually has a single product (Founders Edition) on their page
        product_name = "NVIDIA GeForce RTX 5090 Founders Edition"
        manufacturer = "NVIDIA"
        
        # Find buy button to determine stock status
        buy_button = soup.find('a', {'data-module-name': 'cta', 'data-category-name': 'buy'})
        
        if buy_button and "where to buy" not in buy_button.text.lower():
            # Found direct buy button, product might be in stock
            buy_url = buy_button['href'] if buy_button.has_attr('href') else url
            
            # Check if product exists in database, if not, create it
            product = session.query(Product).filter_by(url=buy_url).first()
            if not product:
                # Extract description and specifications from the page
                description_elem = soup.select_one('.product-description, .description')
                description = description_elem.text.strip() if description_elem else "No description available"
                
                specs_section = soup.select('.specs-section, .specifications-section')
                specifications = "\n".join([spec.text.strip() for spec in specs_section]) if specs_section else "No specifications available"
                
                product = Product(
                    retailer_id=retailer.id,
                    name=product_name,
                    manufacturer=manufacturer,
                    url=buy_url,
                    description=description,
                    specifications=specifications
                )
                session.add(product)
                session.commit()
                logger.info(f"Added new product: {product_name}")
            
            # Extract price (NVIDIA often doesn't show price directly on the product page)
            price_elem = soup.select_one('.product-price, .price')
            price = None
            if price_elem:
                price_text = price_elem.text.strip()
                # Remove currency symbol and commas, then convert to float
                price_text = ''.join(c for c in price_text if c.isdigit() or c == '.')
                price = float(price_text) if price_text else 1999.0  # Default to MSRP if not found
            else:
                price = 1999.0  # Default to MSRP
            
            # Determine in_stock status
            in_stock = "buy now" in buy_button.text.lower() if buy_button else False
            
            # Record price and stock status
            if price:
                price_history = PriceHistory(product_id=product.id, price=price)
                session.add(price_history)
            
            stock_history = StockHistory(product_id=product.id, in_stock=in_stock)
            session.add(stock_history)
            session.commit()
            
            logger.info(f"NVIDIA: {product_name} - Price: ${price if price else 'N/A'} - In Stock: {in_stock}")
            results.append((product, price, in_stock))
        
        else:
            # Handle the "where to buy" case, which links to retailers
            logger.info("NVIDIA directs to external retailers, no direct purchase available")
            
            # Check if product exists in database to track it anyway
            product = session.query(Product).filter_by(url=url, retailer_id=retailer.id).first()
            if not product:
                # Extract description and specifications from the page
                description_elem = soup.select_one('.product-description, .description')
                description = description_elem.text.strip() if description_elem else "No description available"
                
                specs_section = soup.select('.specs-section, .specifications-section')
                specifications = "\n".join([spec.text.strip() for spec in specs_section]) if specs_section else "No specifications available"
                
                product = Product(
                    retailer_id=retailer.id,
                    name=product_name,
                    manufacturer=manufacturer,
                    url=url,
                    description=description,
                    specifications=specifications
                )
                session.add(product)
                session.commit()
                logger.info(f"Added new product (not directly available): {product_name}")
            
            # Record as out of stock
            stock_history = StockHistory(product_id=product.id, in_stock=False)
            session.add(stock_history)
            session.commit()
            
            logger.info(f"NVIDIA: {product_name} - Price: N/A - In Stock: False")
            results.append((product, None, False))
        
        return results
    
    except Exception as e:
        logger.error(f"Error scraping NVIDIA: {e}")
        return results