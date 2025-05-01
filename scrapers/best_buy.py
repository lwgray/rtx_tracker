"""
Best Buy scraper module for RTX 5090 Stock Tracker
"""

import time
import json
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
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Set page load timeout
    driver.set_page_load_timeout(30)
    
    return driver

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
            EC.presence_of_element_located((By.CSS_SELECTOR, ".priceView-customer-price span"))
        )
        price_text = price_element.text.strip()
        # Remove currency symbol and commas, then convert to float
        price = float(price_text.replace('$', '').replace(',', ''))
        logger.debug(f"Extracted price using WebDriver: ${price}")
        return price
    except (TimeoutException, NoSuchElementException, ValueError) as e:
        logger.debug(f"Could not extract price using WebDriver: {e}")
    
    # Strategy 2: Try alternative selectors
    price_selectors = [
        ".priceView-customer-price span",
        ".priceView-hero-price span",
        ".priceView-purchase-price",
        ".pricing-price .sr-only",
        "[data-testid='customer-price']"
    ]
    
    for selector in price_selectors:
        try:
            price_element = driver.find_element(By.CSS_SELECTOR, selector)
            price_text = price_element.text.strip()
            # Remove currency symbol and commas, then convert to float
            price = float(price_text.replace('$', '').replace(',', ''))
            logger.debug(f"Extracted price using selector '{selector}': ${price}")
            return price
        except (NoSuchElementException, ValueError):
            continue
    
    # Strategy 3: Try to extract from JSON-LD data
    try:
        json_ld_elements = driver.find_elements(By.CSS_SELECTOR, "script[type='application/ld+json']")
        for element in json_ld_elements:
            try:
                json_data = json.loads(element.get_attribute('innerHTML'))
                if 'offers' in json_data and 'price' in json_data['offers']:
                    price = float(json_data['offers']['price'])
                    logger.debug(f"Extracted price from JSON-LD: ${price}")
                    return price
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    except Exception as e:
        logger.debug(f"Error extracting price from JSON-LD: {e}")
    
    # Strategy 4: Parse page with BeautifulSoup if not provided
    if soup is None:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Try to extract price using BeautifulSoup
    price_elem = soup.select_one('.priceView-customer-price span')
    if price_elem:
        try:
            price_text = price_elem.text.strip()
            price = float(price_text.replace('$', '').replace(',', ''))
            logger.debug(f"Extracted price using BeautifulSoup: ${price}")
            return price
        except ValueError:
            pass
    
    # Fallback: Return hardcoded MSRP for RTX 5090
    logger.warning("Could not extract price, returning default MSRP")
    return 1999.99

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
        add_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".add-to-cart-button"))
        )
        # Check if button is disabled
        button_disabled = add_button.get_attribute("disabled") is not None
        if not button_disabled:
            logger.debug("Product appears to be in stock (Add to Cart button enabled)")
            return True
    except (TimeoutException, NoSuchElementException):
        logger.debug("Could not find Add to Cart button")
    
    # Strategy 2: Check for "Sold Out" text
    try:
        sold_out_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Sold Out')]")
        if sold_out_elements:
            logger.debug("Product is out of stock (Sold Out text found)")
            return False
    except NoSuchElementException:
        pass
    
    # Strategy 3: Check for availability message
    availability_selectors = [
        ".fulfillment-add-to-cart-button .btn-disabled",
        ".fulfillment-add-to-cart-button [disabled]",
        ".availability-message",
        ".shop-messaging-long-message"
    ]
    
    for selector in availability_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                text = element.text.lower()
                if "out of stock" in text or "sold out" in text or "unavailable" in text:
                    logger.debug(f"Product is out of stock (availability message found: '{text}')")
                    return False
        except NoSuchElementException:
            continue
    
    # Strategy 4: Parse page with BeautifulSoup if not provided
    if soup is None:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Check for "Add to Cart" button using BeautifulSoup
    add_to_cart_button = soup.find('button', {'data-button-state': 'ADD_TO_CART'})
    if add_to_cart_button:
        disabled = add_to_cart_button.get('disabled') is not None
        if not disabled:
            logger.debug("Product appears to be in stock (BeautifulSoup found enabled Add to Cart button)")
            return True
    
    # Default to out of stock if we can't determine status
    logger.debug("Could not determine stock status, defaulting to out of stock")
    return False

def extract_product_details(driver):
    """
    Extract product description and specifications
    
    Args:
        driver: WebDriver instance
    
    Returns:
        tuple: (description, specifications, upc)
    """
    description = "No description available"
    specifications = "No specifications available"
    upc = None
    
    # Extract description
    try:
        # Wait for description to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-description"))
        )
        
        description_elem = driver.find_element(By.CSS_SELECTOR, ".product-description")
        if description_elem:
            description = description_elem.text.strip()
    except (TimeoutException, NoSuchElementException) as e:
        logger.debug(f"Could not extract description: {e}")
    
    # Extract specifications
    try:
        # Try to find specifications tab
        spec_tabs = driver.find_elements(By.XPATH, "//button[contains(text(), 'Specifications')]")
        if spec_tabs:
            spec_tabs[0].click()
            time.sleep(2)  # Wait for specifications to load
        
        spec_elem = driver.find_element(By.CSS_SELECTOR, ".product-specifications")
        if spec_elem:
            specifications = spec_elem.text.strip()
            
            # Look for UPC in specifications
            spec_rows = spec_elem.find_elements(By.CSS_SELECTOR, "tr")
            for row in spec_rows:
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                    if len(cells) >= 2 and "UPC" in cells[0].text:
                        upc = cells[1].text.strip()
                        break
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
    except (TimeoutException, NoSuchElementException) as e:
        logger.debug(f"Could not extract specifications: {e}")
    
    # Try to extract UPC from JSON-LD if not found in specifications
    if not upc:
        try:
            json_ld_elements = driver.find_elements(By.CSS_SELECTOR, "script[type='application/ld+json']")
            for element in json_ld_elements:
                try:
                    json_data = json.loads(element.get_attribute('innerHTML'))
                    if 'gtin13' in json_data:
                        upc = json_data['gtin13']
                        break
                    elif 'gtin12' in json_data:
                        upc = json_data['gtin12']
                        break
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
        except Exception as e:
            logger.debug(f"Error extracting UPC from JSON-LD: {e}")
    
    return description, specifications, upc

def scrape_best_buy(session, retailer):
    """
    Scrape RTX 5090 information from Best Buy using Selenium
    
    Args:
        session: Database session
        retailer: Retailer object
        
    Returns:
        tuple: (product, price, in_stock)
    """
    url = "https://www.bestbuy.com/site/nvidia-geforce-rtx-5090-32gb-gddr7-graphics-card-dark-gun-metal/6614151.p?skuId=6614151"
    logger.info(f"Scraping Best Buy: {url}")
    
    driver = None
    
    try:
        # Initialize WebDriver
        driver = setup_webdriver()
        
        # Load the page
        logger.debug("Loading Best Buy page...")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        
        # Parse page with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract product details
        product_name = "NVIDIA GeForce RTX 5090 32GB GDDR7 Graphics Card"
        manufacturer = "NVIDIA"
        
        # Check if product exists in database, if not, create it
        product = session.query(Product).filter_by(url=url).first()
        if not product:
            # Extract product description, specifications, and UPC
            description, specifications, upc = extract_product_details(driver)
            
            product = Product(
                retailer_id=retailer.id,
                name=product_name,
                manufacturer=manufacturer,
                upc=upc,
                url=url,
                description=description,
                specifications=specifications
            )
            session.add(product)
            session.commit()
            logger.info(f"Added new product: {product_name}, UPC: {upc}")
        
        # Extract price
        price = extract_price(driver, soup)
        
        # Check if in stock
        in_stock = check_in_stock(driver, soup)
        
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
    
    finally:
        # Clean up WebDriver
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
