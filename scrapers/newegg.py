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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers',
        'Cache-Control': 'max-age=0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.newegg.com/',
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
        # Add delay to avoid rate limiting
        import time
        time.sleep(2)  # 2 second delay
        
        response = requests.get(url, headers=get_headers(), timeout=30)
        
        # Log the status code and content length to help with debugging
        logger.info(f"Newegg response status: {response.status_code}, Content length: {len(response.content)}")
        
        if response.status_code != 200:
            logger.error(f"Failed to access Newegg. Status code: {response.status_code}")
            return results
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try different possible selectors that Newegg might be using
        product_items = soup.select('.item-cell')  # Original selector
        
        # If no products found with original selector, try alternatives
        if not product_items:
            logger.info("No items found with .item-cell selector, trying alternatives...")
            # Common alternative selectors
            possible_selectors = [
                '.item-container', '.item-box', '.product-item', 
                '.product-cell', '.product-container', '.item',
                'div[class*="item"]', 'div[class*="product"]',
                '.product-listing-item'
            ]
            
            for selector in possible_selectors:
                product_items = soup.select(selector)
                if product_items:
                    logger.info(f"Found items using selector: {selector}")
                    break
        
        # If still no product items found, try to find any product-related content
        if not product_items:
            logger.warning("No product items found with standard selectors. Trying to extract any product info.")
            # Save the HTML for debugging
            with open('newegg_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info("Saved response HTML to newegg_response.html for debugging")
            
            # Look for any elements that might contain product information
            title_elements = soup.select('a[title*="RTX 5090"]')
            if title_elements:
                logger.info(f"Found {len(title_elements)} title elements containing 'RTX 5090'")
                # Use these elements instead
                product_items = [elem.parent.parent for elem in title_elements]
        
        if not product_items:
            logger.warning("No product items found on Newegg using any selector method")
            return results
        
        logger.info(f"Found {len(product_items)} product items")
        
        for item in product_items[:10]:  # Limit to top 10 results
            try:
                # Extract product details - be flexible in finding elements
                title_elem = None
                # Try different possible title selectors
                for title_selector in ['.item-title', '.product-title', 'a[title]', 'a.title', '.title']:
                    title_elem = item.select_one(title_selector)
                    if title_elem:
                        break
                
                if not title_elem:
                    # Try to find any anchor tag with substantial text
                    anchors = item.find_all('a')
                    for anchor in anchors:
                        if anchor.text and len(anchor.text.strip()) > 10:  # Reasonable title length
                            title_elem = anchor
                            break
                
                if not title_elem:
                    logger.warning(f"Could not find title element in item: {item}")
                    continue
                
                product_name = title_elem.text.strip()
                
                # Skip if not RTX 5090
                if "rtx 5090" not in product_name.lower():
                    continue
                
                # Extract product URL
                product_url = None
                if title_elem.has_attr('href'):
                    product_url = title_elem['href']
                else:
                    # Try to find any anchor tag that might be a product link
                    anchors = item.find_all('a')
                    for anchor in anchors:
                        if anchor.has_attr('href') and len(anchor['href']) > 10:  # Reasonable URL length
                            product_url = anchor['href']
                            break
                
                if not product_url:
                    logger.warning(f"Could not find product URL for: {product_name}")
                    continue
                
                # Ensure the URL is absolute
                if not product_url.startswith('http'):
                    product_url = f"https://www.newegg.com{product_url}" if not product_url.startswith('/') else f"https://www.newegg.com{product_url}"
                
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
                    # Add delay before fetching product details
                    time.sleep(2)
                    
                    # Visit product page to get description and specs
                    try:
                        product_response = requests.get(product_url, headers=get_headers(), timeout=30)
                        if product_response.status_code != 200:
                            logger.warning(f"Failed to access product page: {product_url}. Status: {product_response.status_code}")
                            description = "No description available"
                            specifications = "No specifications available"
                            upc = None
                        else:
                            product_soup = BeautifulSoup(product_response.content, 'html.parser')
                            
                            # Try different selectors for description
                            description_elem = None
                            for desc_selector in ['.product-description', '#product-details', '.details', '.description']:
                                description_elem = product_soup.select_one(desc_selector)
                                if description_elem:
                                    break
                            
                            description = description_elem.text.strip() if description_elem else "No description available"
                            
                            # Try different selectors for specifications
                            specs_elem = None
                            for specs_selector in ['#Specifications', '.specifications', '.specs-table']:
                                specs_elem = product_soup.select_one(specs_selector)
                                if specs_elem:
                                    break
                            
                            upc = None  # Initialize upc to None
                            specifications = "No specifications available"
                            
                            if specs_elem:
                                specifications = specs_elem.text.strip()
                                try:
                                    # Look for UPC in specifications
                                    upc_row = specs_elem.find('tr', string=lambda s: s and 'UPC' in s if s else False)
                                    if upc_row:
                                        upc_cell = upc_row.find_next('td')
                                        if upc_cell:
                                            upc = upc_cell.text.strip()
                                    # If not found in a row, try looking for any text containing UPC
                                    if not upc:
                                        upc_text = specs_elem.find(string=lambda s: s and 'UPC' in s if s else False)
                                        if upc_text:
                                            # Try to extract UPC from text - this is a simplistic approach
                                            upc_parts = upc_text.split('UPC:')
                                            if len(upc_parts) > 1:
                                                upc = upc_parts[1].strip().split()[0]
                                except Exception as e:
                                    logger.warning(f"Error extracting UPC: {e}")
                    except Exception as e:
                        logger.error(f"Error fetching product details: {e}")
                        description = "No description available"
                        specifications = "No specifications available"
                        upc = None
                    
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
                
                # Extract price - be flexible in finding elements
                price = None
                # Try different possible price selectors
                price_selectors = [
                    '.price-current strong', '.price', '.current-price', '.product-price',
                    '[class*="price"]', 'li.price', '.price-main'
                ]
                
                for price_selector in price_selectors:
                    price_elem = item.select_one(price_selector)
                    if price_elem:
                        price_text = price_elem.text.strip()
                        # Try to extract a valid price from the text
                        import re
                        price_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', price_text)
                        if price_match:
                            try:
                                # Remove commas, then convert to float
                                price = float(price_match.group(1).replace(',', ''))
                                break
                            except ValueError:
                                continue
                
                # Extract stock status - flexible approach
                in_stock = True  # Default to in stock unless we find out-of-stock indicator
                out_of_stock_indicators = [
                    '.item-promo .item-info-stock-out', 
                    '.out-of-stock', 
                    '[class*="out-of-stock"]',
                    '.sold-out',
                    '.ship-not-available'
                ]
                
                for indicator in out_of_stock_indicators:
                    if item.select_one(indicator):
                        in_stock = False
                        break
                
                # Also check text content for out-of-stock indicators
                item_text = item.text.lower()
                out_of_stock_texts = ['out of stock', 'sold out', 'not available', 'out_of_stock']
                for text in out_of_stock_texts:
                    if text in item_text:
                        in_stock = False
                        break
                
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
                import traceback
                logger.error(traceback.format_exc())
        
        return results
    
    except Exception as e:
        logger.error(f"Error scraping Newegg: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return results