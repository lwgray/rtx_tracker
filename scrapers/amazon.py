"""
Amazon scraper module for RTX 5090 Stock Tracker
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

def scrape_amazon(session, retailer):
    """
    Scrape RTX 5090 information from Amazon
    
    Args:
        session: Database session
        retailer: Retailer object
        
    Returns:
        list: List of (product, price, in_stock) tuples
    """
    url = "https://www.amazon.com/s?k=rtx+5090"
    logger.info(f"Scraping Amazon: {url}")
    
    results = []
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all product cards
        product_cards = soup.select('div[data-component-type="s-search-result"]')
        
        if not product_cards:
            logger.warning("No product cards found on Amazon")
            return results
        
        for card in product_cards[:10]:  # Limit to top 10 results
            try:
                # Extract product details
                title_elem = card.select_one('h2 a span')
                if not title_elem:
                    continue
                
                product_name = title_elem.text.strip()
                
                # Skip if not RTX 5090
                if "rtx 5090" not in product_name.lower():
                    continue
                
                # Extract product URL
                url_elem = card.select_one('h2 a')
                product_url = "https://www.amazon.com" + url_elem['href'] if url_elem else None
                if not product_url:
                    continue
                
                # Extract manufacturer
                manufacturer = "Unknown"
                if "asus" in product_name.lower():
                    manufacturer = "ASUS"
                elif "msi" in product_name.lower():
                    manufacturer = "MSI"
                elif "evga" in product_name.lower():
                    manufacturer = "EVGA"
                elif "gigabyte" in product_name.lower():
                    manufacturer = "GIGABYTE"
                elif "nvidia" in product_name.lower():
                    manufacturer = "NVIDIA"
                
                # Check if product exists in database, if not, create it
                product = session.query(Product).filter_by(url=product_url).first()
                if not product:
                    # Visit product page to get description and specs
                    product_response = requests.get(product_url, headers=get_headers(), timeout=30)
                    product_soup = BeautifulSoup(product_response.content, 'html.parser')
                    
                    description_elem = product_soup.select_one('#productDescription')
                    description = description_elem.text.strip() if description_elem else "No description available"
                    
                    specs_elem = product_soup.select_one('#techSpecContent')
                    specifications = specs_elem.text.strip() if specs_elem else "No specifications available"
                    
                    product = Product(
                        retailer_id=retailer.id,
                        name=product_name,
                        manufacturer=manufacturer,
                        url=product_url,
                        description=description,
                        specifications=specifications
                    )
                    session.add(product)
                    session.commit()
                    logger.info(f"Added new product: {product_name}")
                
                # Extract price
                price_elem = card.select_one('.a-price .a-offscreen')
                price = None
                if price_elem:
                    price_text = price_elem.text.strip()
                    # Remove currency symbol and commas, then convert to float
                    price = float(price_text.replace('$', '').replace(',', ''))
                
                # Extract stock status
                in_stock = "Currently unavailable" not in card.text
                
                # Record price and stock status
                if price:
                    price_history = PriceHistory(product_id=product.id, price=price)
                    session.add(price_history)
                
                stock_history = StockHistory(product_id=product.id, in_stock=in_stock)
                session.add(stock_history)
                session.commit()
                
                logger.info(f"Amazon: {product_name} - Price: ${price if price else 'N/A'} - In Stock: {in_stock}")
                results.append((product, price, in_stock))
            
            except Exception as e:
                logger.error(f"Error processing Amazon product card: {e}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error scraping Amazon: {e}")
        return results