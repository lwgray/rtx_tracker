"""
Amazon scraper module for RTX 5090 Stock Tracker
"""

import time
import json
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from bs4 import BeautifulSoup
from database.models import Product, PriceHistory, StockHistory
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

def setup_webdriver():
    """Set up a headless Chrome WebDriver for scraping"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Add user-agent to mimic a real browser
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Set page load timeout
    driver.set_page_load_timeout(30)
    
    return driver

def save_debug_content(url, content, filename_prefix="amazon_debug"):
    """Save HTML content for debugging"""
    try:
        # Create debug directory if it doesn't exist
        debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "debug")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Create a sanitized filename from the URL
        url_part = url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_")
        if len(url_part) > 50:
            url_part = url_part[:50]
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(debug_dir, f"{filename_prefix}_{url_part}_{timestamp}.html")
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Saved debug content to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving debug content: {e}")
        return None

def extract_price(driver, soup=None):
    """
    Extract price using multiple fallback strategies
    
    Args:
        driver: WebDriver instance
        soup: BeautifulSoup object (optional)
    
    Returns:
        float: Product price or None if not found
    """
    # Strategy 1: Try to get price from the page using WebDriver
    try:
        price_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "priceblock_ourprice"))
        )
        price_text = price_element.text.strip()
        # Remove currency symbol and commas, then convert to float
        price = float(price_text.replace('$', '').replace(',', ''))
        logger.debug(f"Extracted price using WebDriver (ourprice): ${price}")
        return price
    except (TimeoutException, NoSuchElementException, ValueError) as e:
        logger.debug(f"Could not extract price using WebDriver (ourprice): {e}")
    
    # Strategy 2: Try alternative selectors
    price_selectors = [
        ".a-price .a-offscreen",
        "#price_inside_buybox",
        "#corePrice_feature_div .a-price .a-offscreen",
        "#priceblock_dealprice",
        ".a-section .a-price .a-offscreen",
        "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
        ".priceToPay .a-offscreen",
        "#apex_desktop .a-price .a-offscreen",
        ".a-price"
    ]
    
    for selector in price_selectors:
        try:
            price_elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for price_element in price_elements:
                price_text = price_element.text.strip()
                if not price_text:
                    # Try getting attribute value for elements with no visible text
                    price_text = price_element.get_attribute('innerHTML').strip()
                
                # Skip if empty or non-price text
                if not price_text or not any(c.isdigit() for c in price_text):
                    continue
                
                # Remove currency symbol and commas, then convert to float
                price_match = re.search(r'[$£€]?([0-9,]+\.[0-9]{2})', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))
                    logger.debug(f"Extracted price using selector '{selector}': ${price}")
                    return price
        except (NoSuchElementException, ValueError) as e:
            continue
    
    # Strategy 3: Try to extract from page source using regex
    try:
        page_source = driver.page_source
        price_pattern = r'"price":\s*"?\$?([0-9,]+\.[0-9]{2})"?'
        price_matches = re.findall(price_pattern, page_source)
        if price_matches:
            price = float(price_matches[0].replace(',', ''))
            logger.debug(f"Extracted price using regex: ${price}")
            return price
    except (ValueError, IndexError) as e:
        logger.debug(f"Error extracting price using regex: {e}")
    
    # Strategy 4: Parse page with BeautifulSoup if not provided
    if soup is None:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Try to extract price using BeautifulSoup
    for selector in price_selectors:
        price_elem = soup.select_one(selector)
        if price_elem:
            try:
                price_text = price_elem.text.strip()
                price_match = re.search(r'[$£€]?([0-9,]+\.[0-9]{2})', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))
                    logger.debug(f"Extracted price using BeautifulSoup: ${price}")
                    return price
            except ValueError:
                pass
    
    # Default fallback: no price found
    logger.warning("Could not extract price from Amazon")
    return None

def check_in_stock(driver, soup=None):
    """
    Check if the product is in stock using multiple strategies
    
    Args:
        driver: WebDriver instance
        soup: BeautifulSoup object (optional)
    
    Returns:
        bool: True if in stock, False otherwise
    """
    # Strategy 1: Check for "Add to Cart" button
    try:
        add_buttons = driver.find_elements(By.ID, "add-to-cart-button")
        if add_buttons and add_buttons[0].is_displayed():
            logger.debug("Product appears to be in stock (Add to Cart button found)")
            return True
        
        # Try alternative add to cart buttons
        add_buttons = driver.find_elements(By.CSS_SELECTOR, 
                                          "[name='submit.add-to-cart'], #add-to-cart-button-ubb, .a-button-input[value*='Add to Cart']")
        if add_buttons and any(btn.is_displayed() and not btn.get_attribute("disabled") for btn in add_buttons):
            logger.debug("Product appears to be in stock (alternative Add to Cart button found)")
            return True
    except (NoSuchElementException, IndexError):
        logger.debug("Could not find Add to Cart button")
    
    # Strategy 2: Check for "Out of Stock" text
    out_of_stock_texts = [
        "Currently unavailable",
        "Out of Stock",
        "Temporarily out of stock",
        "We don't know when or if this item will be back in stock"
    ]
    
    page_text = driver.page_source.lower()
    for text in out_of_stock_texts:
        if text.lower() in page_text:
            logger.debug(f"Product is out of stock ('{text}' found)")
            return False
    
    # Strategy 3: Check for availability section
    try:
        availability = driver.find_element(By.ID, "availability")
        if availability:
            availability_text = availability.text.lower()
            if "in stock" in availability_text:
                logger.debug("Product is in stock (availability section)")
                return True
            elif "out of stock" in availability_text or "unavailable" in availability_text:
                logger.debug("Product is out of stock (availability section)")
                return False
    except NoSuchElementException:
        # Try alternative availability selectors
        try:
            availability = driver.find_element(By.CSS_SELECTOR, "#availability_feature_div, .availabilityMessage")
            if availability:
                availability_text = availability.text.lower()
                if "in stock" in availability_text:
                    logger.debug("Product is in stock (alternative availability section)")
                    return True
                elif "out of stock" in availability_text or "unavailable" in availability_text:
                    logger.debug("Product is out of stock (alternative availability section)")
                    return False
        except NoSuchElementException:
            pass
    
    # Strategy 4: Parse page with BeautifulSoup if not provided
    if soup is None:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Check for "Add to Cart" button using BeautifulSoup
    add_to_cart_button = soup.find('input', {'id': 'add-to-cart-button'})
    if add_to_cart_button:
        logger.debug("Product appears to be in stock (BeautifulSoup found Add to Cart button)")
        return True
    
    # Final check: Look for "Add to Cart" text anywhere
    if "add to cart" in page_text:
        return True
    
    # Default to out of stock if we can't determine status
    logger.debug("Could not determine stock status for Amazon, defaulting to out of stock")
    return False

def extract_product_details(driver, product_title):
    """
    Extract product description, specifications, and UPC/ASIN
    
    Args:
        driver: WebDriver instance
        product_title: Title of the product
    
    Returns:
        tuple: (description, specifications, upc)
    """
    description = "No description available"
    specifications = "No specifications available"
    upc = None
    
    # Extract ASIN from URL or page
    try:
        url = driver.current_url
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
        if asin_match:
            asin = asin_match.group(1)
            upc = f"ASIN:{asin}"  # Use ASIN as UPC placeholder
    except Exception as e:
        logger.debug(f"Could not extract ASIN from URL: {e}")
    
    # Extract description
    try:
        description_elem = driver.find_element(By.ID, "productDescription")
        if description_elem:
            description = description_elem.text.strip()
    except NoSuchElementException:
        # Try alternative selectors
        description_selectors = [
            "#feature-bullets",
            "#productDescription_feature_div",
            "#dpx-product-description_feature_div",
            "div[data-feature-name='productDescription']",
            "#aplus",
            "#aplus_feature_div"
        ]
        
        for selector in description_selectors:
            try:
                description_elem = driver.find_element(By.CSS_SELECTOR, selector)
                if description_elem:
                    description = description_elem.text.strip()
                    if len(description) > 20:  # Reasonable description length
                        break
            except NoSuchElementException:
                continue
    
    # Extract specifications
    try:
        # Click on the Technical Details tab if it exists
        tech_details_tab = driver.find_elements(By.XPATH, "//a[contains(text(), 'Technical Details')]")
        if tech_details_tab:
            tech_details_tab[0].click()
            time.sleep(2)  # Wait for specifications to load
        
        # Try to find the specifications table
        spec_tables = driver.find_elements(By.ID, "productDetails_techSpec_section_1")
        if not spec_tables:
            spec_tables = driver.find_elements(By.CSS_SELECTOR, ".prodDetTable, #productDetails, #detailBulletsWrapper_feature_div")
        
        if spec_tables:
            specifications = spec_tables[0].text.strip()
            
            # Look for UPC in specifications
            spec_text = specifications.lower()
            if not upc:
                upc_patterns = [
                    r'upc\s*:?\s*(\d{12,13})',
                    r'upc.*?(\d{12,13})',
                    r'ean\s*:?\s*(\d{13})',
                    r'gtin\s*:?\s*(\d{14})'
                ]
                
                for pattern in upc_patterns:
                    match = re.search(pattern, spec_text)
                    if match:
                        upc = match.group(1)
                        break
        
        # If no specification table found, try to get it from the bullet points
        if specifications == "No specifications available":
            bullets = driver.find_elements(By.CSS_SELECTOR, "#feature-bullets ul li")
            if bullets:
                specifications = "\n".join([bullet.text for bullet in bullets])
    except (NoSuchElementException, StaleElementReferenceException) as e:
        logger.debug(f"Could not extract specifications: {e}")
    
    # If no UPC found and we have an ASIN, use it
    if not upc and 'asin' in locals():
        upc = f"ASIN:{asin}"
    
    return description, specifications, upc

def search_rtx_5090(driver):
    """
    Search for RTX 5090 products on Amazon
    
    Args:
        driver: WebDriver instance
        
    Returns:
        list: List of URLs for RTX 5090 products
    """
    search_url = "https://www.amazon.com/s?k=rtx+5090"
    logger.info(f"Searching Amazon for RTX 5090: {search_url}")
    
    try:
        driver.get(search_url)
        
        # Wait for search results to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".s-result-item"))
        )
        
        # Save search results for debugging
        save_debug_content(search_url, driver.page_source)
        
        # Get search results
        results = driver.find_elements(By.CSS_SELECTOR, ".s-result-item[data-component-type='s-search-result']")
        
        if not results:
            # Try alternative selectors
            results = driver.find_elements(By.CSS_SELECTOR, ".s-result-item, .sg-col-4-of-12, div[data-asin]")
        
        logger.info(f"Found {len(results)} search results")
        
        # Extract product URLs
        product_urls = []
        for result in results:
            try:
                # Find the link to the product
                links = result.find_elements(By.CSS_SELECTOR, "h2 a, .a-link-normal.a-text-normal")
                
                for link in links:
                    url = link.get_attribute("href")
                    if not url:
                        continue
                    
                    # Verify it's a GPU product by checking the title and URL
                    title = link.text.lower()
                    if "rtx" in title or "geforce" in title or "graphics card" in title:
                        # Check for 5090 specifically
                        if "5090" in title or "5090" in url:
                            if url not in product_urls:  # Avoid duplicates
                                product_urls.append(url)
                                logger.info(f"Found RTX 5090 product: {title} - {url}")
                    
                    if len(product_urls) >= 10:  # Limit to 10 products
                        break
            except (NoSuchElementException, StaleElementReferenceException) as e:
                logger.debug(f"Error processing search result: {e}")
                continue
        
        # If no products found with specific search, try broader search
        if not product_urls:
            logger.info("No specific RTX 5090 products found, trying broader search")
            
            # Look for any product link that might be related
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                try:
                    url = link.get_attribute("href")
                    if not url:
                        continue
                    
                    # Check if link has RTX in URL or text
                    if "rtx" in url.lower() or "nvidia" in url.lower():
                        text = link.text.strip()
                        if text and len(text) > 5:  # Skip empty or very short text
                            logger.info(f"Found potential GPU link: {text} - {url}")
                            if url not in product_urls:
                                product_urls.append(url)
                        
                        if len(product_urls) >= 10:
                            break
                except Exception:
                    continue
        
        # Try direct product links as fallback
        if not product_urls:
            logger.info("Using fallback direct product links")
            direct_links = [
                "https://www.amazon.com/NVIDIA-GeForce-Graphics-Memory-DisplayPort/dp/B0BYHT3S2F",
                # Add more direct links to known RTX 5090 products if available
            ]
            product_urls.extend(direct_links)
        
        logger.info(f"Found {len(product_urls)} RTX 5090 products on Amazon")
        return product_urls
    
    except Exception as e:
        logger.error(f"Error searching Amazon for RTX 5090: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def scrape_amazon(session, retailer):
    """
    Scrape RTX 5090 information from Amazon using Selenium
    
    Args:
        session: Database session
        retailer: Retailer object
        
    Returns:
        list: List of tuples (product, price, in_stock)
    """
    logger.info("Starting Amazon scraper")
    
    driver = None
    results = []
    
    try:
        # Initialize WebDriver
        driver = setup_webdriver()
        
        # Search for RTX 5090 products
        product_urls = search_rtx_5090(driver)
        
        # Scrape each product
        for url in product_urls:
            try:
                logger.info(f"Scraping Amazon product: {url}")
                
                # Load the product page
                driver.get(url)
                
                # Wait for page to load
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.ID, "productTitle"))
                    )
                except TimeoutException:
                    logger.warning(f"Timeout waiting for product page to load: {url}")
                    # Continue anyway - some elements might be loaded
                
                # Save page source for debugging
                save_debug_content(url, driver.page_source, "amazon_product")
                
                # Extract product title
                try:
                    title_elem = driver.find_element(By.ID, "productTitle")
                    product_title = title_elem.text.strip()
                except NoSuchElementException:
                    logger.warning("Could not find product title, checking for any heading")
                    
                    # Try to find any heading that might be the title
                    try:
                        headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2")
                        for heading in headings:
                            text = heading.text.strip()
                            if text and len(text) > 10 and ("rtx" in text.lower() or "nvidia" in text.lower()):
                                product_title = text
                                break
                        
                        if not 'product_title' in locals():
                            logger.warning("Could not find product title, skipping")
                            continue
                    except Exception:
                        logger.warning("Could not find any heading as title, skipping")
                        continue
                
                # Check if this is actually an RTX 5090
                if "rtx" not in product_title.lower() or "5090" not in product_title.lower():
                    logger.warning(f"Not an RTX 5090 product: {product_title}, skipping")
                    continue
                
                # Determine manufacturer (default to NVIDIA if not specified)
                manufacturer = "NVIDIA"
                manufacturer_patterns = [
                    "NVIDIA", "ASUS", "GIGABYTE", "MSI", "EVGA", "PNY", "Zotac"
                ]
                
                for pattern in manufacturer_patterns:
                    if pattern.upper() in product_title.upper():
                        manufacturer = pattern
                        break
                
                # Check if product exists in database, if not, create it
                product = session.query(Product).filter_by(url=url).first()
                if not product:
                    # Extract product description, specifications, and UPC
                    description, specifications, upc = extract_product_details(driver, product_title)
                    
                    product = Product(
                        retailer_id=retailer.id,
                        name=product_title,
                        manufacturer=manufacturer,
                        upc=upc,
                        url=url,
                        description=description,
                        specifications=specifications
                    )
                    session.add(product)
                    session.commit()
                    logger.info(f"Added new product: {product_title}, UPC: {upc}")
                
                # Parse page with BeautifulSoup for price and stock extraction
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Extract price
                price = extract_price(driver, soup)
                
                # Check stock status
                in_stock = check_in_stock(driver, soup)
                
                # Record price and stock status
                if price:
                    price_history = PriceHistory(product_id=product.id, price=price)
                    session.add(price_history)
                
                stock_history = StockHistory(product_id=product.id, in_stock=in_stock)
                session.add(stock_history)
                session.commit()
                
                logger.info(f"Amazon: {product_title} - Price: ${price if price else 'N/A'} - In Stock: {in_stock}")
                results.append((product, price, in_stock))
            
            except Exception as e:
                logger.error(f"Error processing Amazon product: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        return results
    
    except Exception as e:
        logger.error(f"Error in Amazon scraper: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return results
    
    finally:
        # Clean up WebDriver
        if driver:
            try:
                driver.quit()
                logger.info("WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
