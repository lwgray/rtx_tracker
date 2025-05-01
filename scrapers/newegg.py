"""
Newegg scraper module for RTX 5090 Stock Tracker
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

def scrape_newegg(session, retailer):
    """
    Scrape RTX 5090 information from Newegg
    
    Args:
        session: Database session
        retailer: Retailer object
        
    Returns:
        list: List of (product, price, in_stock) tuples
    """
    url = "https://www.newegg.com/p/pl?d=rtx+5090"
    logger.info(f"Scraping Newegg: {url}")
    
    results = []
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all product items
        product_items = soup.select('.item-cell')
        
        if not product_items:
            logger.warning("No product items found on Newegg")
            return results
        
        for item in product_items[:10]:  # Limit to top 10 results
            try:
                # Extract product details
                title_elem = item.select_one('.item-title')
                if not title_elem:
                    continue
                
                product_name = title_elem.text.strip()
                
                # Skip if not RTX 5090
                if "rtx 5090" not in product_name.lower():
                    continue
                
                # Extract product URL
                product_url = title_elem['href'] if title_elem.has_attr('href') else None
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
                elif "zotac" in product_name.lower():
                    manufacturer = "ZOTAC"
                
                # Check if product exists in database, if not, create it
                product = session.query(Product).filter_by(url=product_url).first()
                if not product:
                    # Visit product page to get description and specs
                    product_response = requests.get(product_url, headers=get_headers(), timeout=30)
                    product_soup = BeautifulSoup(product_response.content, 'html.parser')
                    
                    description_elem = product_soup.select_one('.product-description')
                    description = description_elem.text.strip() if description_elem else "No description available"
                    
                    specs_elem = product_soup.select_one('#Specifications')
                    if specs_elem:
                        upc_row = specs_elem.find('tr', string=lambda s: s and 'UPC' in s)
                        if upc_row:
                            upc_cell = upc_row.find_next('td')
                            if upc_cell:
                                upc = upc_cell.text.strip()
                    specifications = specs_elem.text.strip() if specs_elem else "No specifications available"
                    
                    product = Product(
                        retailer_id=retailer.id,
                        name=product_name,
                        manufacturer=manufacturer,
                        upc=upc,
                        url=product_url,
                        description=description,
                        specifications=specifications
                    )
                    session.add(product)
                    session.commit()
                    logger.info(f"Added new product: {product_name}")
                
                # Extract price
                price_elem = item.select_one('.price-current strong')
                if price_elem:
                    price_text = price_elem.text.strip()
                    # Extract cents
                    cents_elem = item.select_one('.price-current sup')
                    cents = cents_elem.text.strip() if cents_elem else "00"
                    price_text = f"{price_text}.{cents}"
                    # Remove commas, then convert to float
                    price = float(price_text.replace(',', ''))
                else:
                    price = None
                
                # Extract stock status
                in_stock = not item.select_one('.item-promo .item-info-stock-out')
                
                # Record price and stock status
                if price:
                    price_history = PriceHistory(product_id=product.id, price=price)
                    session.add(price_history)
                
                stock_history = StockHistory(product_id=product.id, in_stock=in_stock)
                session.add(stock_history)
                session.commit()
                
                logger.info(f"Newegg: {product_name} - Price: ${price if price else 'N/A'} - In Stock: {in_stock}")
                results.append((product, price, in_stock))
            
            except Exception as e:
                logger.error(f"Error processing Newegg product item: {e}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error scraping Newegg: {e}")
        return results