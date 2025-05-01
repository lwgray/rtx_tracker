"""
B&H Photo scraper module for RTX 5090 Stock Tracker
"""

import requests
import re
import time
import random
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
        'Referer': 'https://www.bhphotovideo.com/',
        'Cache-Control': 'max-age=0',
        'TE': 'Trailers',
    }

def scrape_bh_photo(session, retailer):
    """
    Scrape RTX 5090 information from B&H Photo
    
    Args:
        session: Database session
        retailer: Retailer object
        
    Returns:
        list: List of (product, price, in_stock) tuples
    """
    # Try multiple URLs and selectors to find products
    search_urls = [
        "https://www.bhphotovideo.com/c/search?q=rtx%205090",
        "https://www.bhphotovideo.com/c/search?q=rtx+5090&sts=ma",
        "https://www.bhphotovideo.com/c/buy/Graphics-Cards/ci/6567/N/3668461590"
    ]
    
    results = []
    
    for url in search_urls:
        logger.info(f"Scraping B&H Photo: {url}")
        
        try:
            # Add a random delay between requests
            time.sleep(random.uniform(1, 3))
            
            response = requests.get(url, headers=get_headers(), timeout=45)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple CSS selectors for product listings
            selectors = [
                '.productBox', 
                '.c31n4', 
                'div[data-selenium="miniProductPage"]',
                '.item-container'
            ]
            
            for selector in selectors:
                product_items = soup.select(selector)
                if product_items:
                    logger.info(f"Found {len(product_items)} products with selector '{selector}'")
                    break
            
            if not product_items:
                logger.warning(f"No product items found on B&H Photo with URL: {url}")
                
                # Try to check page structure when no products found
                page_title = soup.title.text if soup.title else "No title"
                logger.info(f"Page title: {page_title}")
                
                # Look for any error messages
                error_msgs = soup.select('.error-message, .alert, .notification')
                if error_msgs:
                    for err in error_msgs:
                        logger.warning(f"Error message on page: {err.text.strip()}")
                
                continue  # Try next URL
            
            for item in product_items[:10]:  # Limit to top 10 results
                try:
                    # Try different selectors for title
                    title_selectors = [
                        '.productNameText', 
                        '.product-name',
                        'h5', 
                        '[data-selenium="miniProductPageProductName"]'
                    ]
                    
                    title_elem = None
                    for title_selector in title_selectors:
                        title_elem = item.select_one(title_selector)
                        if title_elem:
                            break
                    
                    if not title_elem:
                        logger.warning("Could not find product title")
                        continue
                    
                    product_name = title_elem.text.strip()
                    
                    # Check if this is an RTX 5090 product
                    if not re.search(r'(rtx\s*5090|geforce\s*rtx\s*5090)', product_name.lower()):
                        logger.info(f"Skipping non-RTX 5090 product: {product_name}")
                        continue
                    
                    # Try different selectors for product URL
                    url_selectors = [
                        'a.productNameText', 
                        'a.product-name',
                        'a[data-selenium="miniProductPageProductNameLink"]',
                        'h5 a'
                    ]
                    
                    url_elem = None
                    for url_selector in url_selectors:
                        url_elem = item.select_one(url_selector)
                        if url_elem and url_elem.has_attr('href'):
                            break
                    
                    if not url_elem or not url_elem.has_attr('href'):
                        logger.warning("Could not find product URL")
                        continue
                    
                    product_url = "https://www.bhphotovideo.com" + url_elem['href'] if not url_elem['href'].startswith('http') else url_elem['href']
                    
                    # Extract manufacturer - try different methods
                    manufacturer = "Unknown"
                    
                    # Method 1: Look for manufacturer element
                    manufacturer_elem = item.select_one('.productMfgText, .brand, [data-selenium="miniProductPageProductBrandName"]')
                    if manufacturer_elem:
                        manufacturer = manufacturer_elem.text.strip()
                    # Method 2: Extract from product name
                    else:
                        manufacturers = ["ASUS", "MSI", "GIGABYTE", "EVGA", "NVIDIA", "ZOTAC", "PNY"]
                        for mfg in manufacturers:
                            if mfg.lower() in product_name.lower():
                                manufacturer = mfg
                                break
                    
                    # Check if product exists in database, if not, create it
                    product = session.query(Product).filter_by(url=product_url).first()
                    if not product:
                        try:
                            # Add a small delay before fetching product details
                            time.sleep(random.uniform(1, 2))
                            
                            # Get product details page
                            product_response = requests.get(product_url, headers=get_headers(), timeout=45)
                            product_soup = BeautifulSoup(product_response.content, 'html.parser')
                            
                            # Try different selectors for description
                            description_selectors = [
                                '.overviewTab', 
                                '.description',
                                '[data-selenium="productDescription"]'
                            ]
                            
                            description = "No description available"
                            for desc_selector in description_selectors:
                                desc_elem = product_soup.select_one(desc_selector)
                                if desc_elem:
                                    description = desc_elem.text.strip()
                                    break
                            
                            # Try different selectors for specifications
                            specs_selectors = [
                                '#specsContent', 
                                '.specs',
                                '.specifications',
                                '[data-selenium="specificationsSection"]'
                            ]
                            
                            specifications = "No specifications available"
                            for specs_selector in specs_selectors:
                                specs_elem = product_soup.select_one(specs_selector)
                                if specs_elem:
                                    specifications = specs_elem.text.strip()
                                    break
                            
                            # Create new product
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
                        
                        except Exception as e:
                            logger.error(f"Error fetching product details: {e}")
                            continue
                    
                    # Extract price - try different selectors
                    price = None
                    price_selectors = [
                        '.price', 
                        '.finalPrice',
                        '[data-selenium="uppedDecimalPriceFirst"]',
                        '.price-current'
                    ]
                    
                    for price_selector in price_selectors:
                        price_elem = item.select_one(price_selector)
                        if price_elem:
                            try:
                                price_text = price_elem.text.strip()
                                # Remove currency symbol and commas, then convert to float
                                price_text = price_text.replace('$', '').replace(',', '')
                                # Extract first valid price pattern
                                price_match = re.search(r'([0-9]+\.?[0-9]*)', price_text)
                                if price_match:
                                    price = float(price_match.group(1))
                                    break
                            except Exception as e:
                                logger.warning(f"Error parsing price: {e}")
                    
                    # Extract stock status
                    in_stock = False
                    
                    # Method 1: Check for "Add to Cart" button
                    cart_buttons = item.select('button:contains("Add to Cart"), button:contains("Add To Cart"), [data-selenium="addToCartButton"]')
                    if cart_buttons and not any('disabled' in btn.get('class', []) for btn in cart_buttons):
                        in_stock = True
                    
                    # Method 2: Check for stock text
                    if not in_stock:
                        stock_texts = ['In Stock', 'Ready to Ship', 'Available']
                        item_text = item.text.lower()
                        in_stock = any(stock_text.lower() in item_text for stock_text in stock_texts)
                    
                    # Record price and stock status
                    if price:
                        price_history = PriceHistory(product_id=product.id, price=price)
                        session.add(price_history)
                    
                    stock_history = StockHistory(product_id=product.id, in_stock=in_stock)
                    session.add(stock_history)
                    session.commit()
                    
                    logger.info(f"B&H Photo: {product_name} - Price: ${price if price else 'N/A'} - In Stock: {in_stock}")
                    results.append((product, price, in_stock))
                
                except Exception as e:
                    logger.error(f"Error processing B&H Photo product item: {e}")
            
            # If we found products, no need to try other URLs
            if results:
                break
        
        except Exception as e:
            logger.error(f"Error scraping B&H Photo URL {url}: {e}")
    
    if not results:
        logger.warning("No RTX 5090 products found on B&H Photo after trying all URLs")
    
    return results