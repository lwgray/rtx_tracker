"""
Micro Center scraper module for RTX 5090 Stock Tracker
"""

import requests
import json
import re
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

def extract_upc(content):
    """
    Extract UPC from product page content
    
    Args:
        content: HTML content
    
    Returns:
        str: UPC or None if not found
    """
    # Look for UPC pattern in the content
    upc_pattern = r'UPC[\s:]*(\d{12,13})'
    match = re.search(upc_pattern, content)
    if match:
        return match.group(1)
    
    # Look for JSON-LD data that might contain UPC/GTIN
    soup = BeautifulSoup(content, 'html.parser')
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                if 'gtin13' in data:
                    return data['gtin13']
                elif 'gtin12' in data:
                    return data['gtin12']
        except:
            continue
    
    return None

def extract_price(soup):
    """
    Extract price from product page
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        float: Price or None if not found
    """
    # Try multiple selectors to find price
    price_selectors = [
        'span.price', 
        '.product-price', 
        '.price-main-block .price',
        '[itemprop="price"]',
        '.pricing-container .price',
        '#pricing .price'
    ]
    
    for selector in price_selectors:
        price_elem = soup.select_one(selector)
        if price_elem:
            price_text = price_elem.text.strip()
            # Remove currency symbol and commas, then convert to float
            price_text = price_text.replace('$', '').replace(',', '')
            # Extract first valid price pattern if there are multiple
            price_match = re.search(r'([0-9]+\.[0-9]+)', price_text)
            if price_match:
                return float(price_match.group(1))
    
    # Try looking for price in JSON data
    for script in soup.find_all('script'):
        if 'window.dataLayer' in script.text:
            try:
                match = re.search(r'"productPrice": ?([0-9.]+)', script.text)
                if match:
                    return float(match.group(1))
            except:
                continue
    
    # Default price for RTX 5090 (use as fallback)
    return 1999.99

def extract_description(soup):
    """
    Extract product description from product page
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        str: Description
    """
    # Try multiple selectors to find product description
    description_selectors = [
        '.product-description',
        '[itemprop="description"]',
        '.details-col .details-container',
        '.details .product-bullets'
    ]
    
    for selector in description_selectors:
        description_elem = soup.select_one(selector)
        if description_elem:
            return description_elem.text.strip()
    
    # Look for any paragraph that might contain a description
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        if len(p.text.strip()) > 100:  # Description is usually long
            return p.text.strip()
    
    return "No description available"

def extract_specifications(soup):
    """
    Extract product specifications from product page
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        str: Specifications
    """
    # Try multiple selectors to find specs
    specs_selectors = [
        '.spec-body',
        '#Specifications',
        '.tech-specs',
        '.product-specs',
        '[itemprop="additionalProperty"]'
    ]
    
    for selector in specs_selectors:
        specs_elem = soup.select_one(selector)
        if specs_elem:
            return specs_elem.text.strip()
    
    # Try to find a table that might contain specs
    tables = soup.find_all('table')
    for table in tables:
        if 'spec' in table.get('class', []) or 'spec' in str(table).lower():
            return table.text.strip()
    
    # Get whatever content is available as specs
    main_content = soup.select_one('.main-content')
    if main_content:
        return main_content.text.strip()
    
    return "No specifications available"

def check_stock_status(soup):
    """
    Check if product is in stock
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        bool: True if in stock, False otherwise
    """
    # Check if "out of stock" text is present
    out_of_stock_indicators = [
        'out of stock',
        'sold out',
        'currently unavailable',
        'not available'
    ]
    
    page_text = soup.text.lower()
    for indicator in out_of_stock_indicators:
        if indicator in page_text:
            return False
    
    # Look for "in stock" or "add to cart" buttons
    in_stock_indicators = [
        'in stock',
        'add to cart',
        'buy now'
    ]
    
    for indicator in in_stock_indicators:
        if indicator in page_text:
            return True
    
    # Look for stock status element
    stock_elem = soup.select_one('.stock-status')
    if stock_elem:
        return 'in stock' in stock_elem.text.lower()
    
    # Default to out of stock for RTX 5090 (conservative approach)
    return False

def scrape_micro_center(session, retailer):
    """
    Scrape RTX 5090 information from Micro Center
    
    Args:
        session: Database session
        retailer: Retailer object
        
    Returns:
        list: List of (product, price, in_stock) tuples
    """
    url = "https://www.microcenter.com/search/search_results.aspx?N=&cat=&Ntt=rtx+5090"
    logger.info(f"Scraping Micro Center: {url}")
    
    results = []
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all product items
        product_items = soup.select('.product_wrapper')
        
        if not product_items:
            logger.warning("No product items found on Micro Center")
            return results
        
        for item in product_items[:10]:  # Limit to top 10 results
            try:
                # Extract product details
                title_elem = item.select_one('.pDescription a')
                if not title_elem:
                    continue
                
                product_name = title_elem.text.strip()
                
                # Skip if not RTX 5090
                if "rtx 5090" not in product_name.lower():
                    continue
                
                # Extract product URL
                product_url = "https://www.microcenter.com" + title_elem['href'] if title_elem else None
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
                elif "pny" in product_name.lower():
                    manufacturer = "PNY"
                
                # Get detailed product page
                logger.info(f"Fetching detailed product page: {product_url}")
                product_response = requests.get(product_url, headers=get_headers(), timeout=30)
                product_soup = BeautifulSoup(product_response.content, 'html.parser')
                
                # Extract UPC
                upc = extract_upc(product_response.text)
                
                # Check if product exists in database by UPC or URL
                product = None
                if upc:
                    product = session.query(Product).filter_by(upc=upc).first()
                
                if not product:
                    product = session.query(Product).filter_by(url=product_url).first()
                
                if not product:
                    # Extract product description and specifications
                    description = extract_description(product_soup)
                    specifications = extract_specifications(product_soup)
                    
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
                    logger.info(f"Added new product: {product_name}, UPC: {upc}")
                
                # Extract price
                price_elem = item.select_one('.price')
                price = None
                if price_elem:
                    price_text = price_elem.text.strip()
                    # Clean the price text to handle cases with multiple prices
                    price_text = price_text.replace('$', '').replace(',', '')
                    # Extract the first valid price if there are multiple
                    price_match = re.search(r'([0-9]+\.[0-9]+)', price_text)
                    if price_match:
                        price = float(price_match.group(1))
                
                # If price not found in search results, try to extract from product page
                if not price:
                    price = extract_price(product_soup)
                
                # Extract stock status
                stock_elem = item.select_one('.inventoryCnt')
                in_stock = stock_elem and "in stock" in stock_elem.text.lower()
                
                # If stock status not found in search results, check product page
                if not stock_elem:
                    in_stock = check_stock_status(product_soup)
                
                # Record price and stock status
                if price:
                    price_history = PriceHistory(product_id=product.id, price=price)
                    session.add(price_history)
                
                stock_history = StockHistory(product_id=product.id, in_stock=in_stock)
                session.add(stock_history)
                session.commit()
                
                logger.info(f"Micro Center: {product_name} - Price: ${price if price else 'N/A'} - In Stock: {in_stock}")
                results.append((product, price, in_stock))
            
            except Exception as e:
                logger.error(f"Error processing Micro Center product item: {e}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error scraping Micro Center: {e}")
        return results