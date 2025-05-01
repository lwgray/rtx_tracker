"""
Best Buy scraper module for RTX 5090 Stock Tracker using Selenium
"""

import os
import time
import random
import json
import re
import logging
import platform
import subprocess
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from database.models import Product, PriceHistory, StockHistory
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

def setup_webdriver(headless=True):
    """
    Set up a Selenium WebDriver
    
    Args:
        headless: Whether to run browser in headless mode
        
    Returns:
        WebDriver object
    """
    options = Options()
    
    if headless:
        options.add_argument('--headless')
    
    # Add additional options to make the browser more stealthy
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Add a realistic user agent
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Disable logging
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # Disable images to speed up the loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    # Get system info
    system = platform.system()
    logger.info(f"Running on {system} platform")
    
    try:
        # Check if we're on Heroku
        if 'DYNO' in os.environ:
            logger.info("Running on Heroku")
            options.binary_location = "/app/.chrome-for-testing/chrome-linux64/chrome"
            service = Service("/app/.chrome-for-testing/chromedriver-linux64/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
        else:
            # For local development
            if system == "Darwin":  # MacOS
                # On macOS, try to use the system Chrome first
                try:
                    # First attempt: Try using the installed Chrome directly
                    logger.info("Trying to use the installed Chrome on macOS")
                    driver = webdriver.Chrome(options=options)
                    logger.info("Successfully created Chrome driver using system Chrome")
                    return driver
                except Exception as e:
                    logger.warning(f"Could not use system Chrome: {e}")
                    # Second attempt: Try with ChromeDriverManager
                    try:
                        # Get Chrome driver path from ChromeDriverManager
                        chrome_driver_path = ChromeDriverManager().install()
                        logger.info(f"ChromeDriverManager installed driver at: {chrome_driver_path}")
                        
                        # Ensure the chromedriver is executable
                        subprocess.run(['chmod', '+x', chrome_driver_path], check=True)
                        logger.info(f"Set executable permissions for {chrome_driver_path}")
                        
                        service = Service(chrome_driver_path)
                        driver = webdriver.Chrome(service=service, options=options)
                        logger.info("Successfully created Chrome driver using ChromeDriverManager")
                        return driver
                    except Exception as e2:
                        logger.error(f"Error setting up Chrome with ChromeDriverManager: {e2}")
                        
                        # Third attempt: Try with system Chrome paths
                        chrome_paths = [
                            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                            '/Applications/Chrome.app/Contents/MacOS/Chrome'
                        ]
                        for chrome_path in chrome_paths:
                            if os.path.exists(chrome_path):
                                logger.info(f"Found Chrome at {chrome_path}")
                                options.binary_location = chrome_path
                                try:
                                    driver = webdriver.Chrome(options=options)
                                    return driver
                                except Exception as e3:
                                    logger.warning(f"Failed with Chrome at {chrome_path}: {e3}")
                        
                        raise Exception("All methods failed to create Chrome driver on macOS")
            else:
                # For Linux or Windows
                logger.info("Using ChromeDriverManager to get Chrome driver")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
        
        # Set window size
        driver.set_window_size(1920, 1080)
        
        # Execute JavaScript to hide the fact we're using Selenium
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("WebDriver successfully initialized")
        return driver
    
    except Exception as e:
        logger.error(f"Error setting up WebDriver: {e}")
        # Let's try one more approach as a last resort
        try:
            logger.info("Trying fallback approach with default Chrome")
            driver = webdriver.Chrome(options=options)
            logger.info("WebDriver initialized with fallback method")
            return driver
        except Exception as e2:
            logger.error(f"Failed to initialize WebDriver with fallback method: {e2}")
            return None

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
        # Initialize Selenium WebDriver
        driver = setup_webdriver(headless=True)
        
        if not driver:
            logger.error("Failed to initialize WebDriver")
            return None, None, False
        
        # Add a random delay to mimic human behavior
        time.sleep(random.uniform(2, 5))
        
        # Navigate to the product page
        driver.get(url)
        
        # Wait for the page to load completely
        wait = WebDriverWait(driver, 30)
        
        try:
            # Try multiple common elements with a shorter timeout
            selectors = [
                '.shop-product-title',
                '.sku-title', 
                '.heading-5',
                'h1',  # Any h1 header
                '.product-title',
                'title', # Even the page title is okay
                'body'  # Body tag as a last resort
            ]
            
            found_element = False
            for selector in selectors:
                try:
                    # Use a shorter timeout for each selector
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    logger.info(f"Page loaded successfully, found element with selector: {selector}")
                    found_element = True
                    break
                except TimeoutException:
                    continue
            
            if not found_element:
                logger.warning("Could not find any expected elements, but continuing anyway")
                # Take a screenshot for debugging if needed
                try:
                    screenshot_path = f"best_buy_debug_{int(time.time())}.png"
                    driver.save_screenshot(screenshot_path)
                    logger.info(f"Saved debug screenshot to {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Could not save debug screenshot: {e}")
        except TimeoutException:
            logger.warning("Timeout waiting for page to load. Proceeding anyway.")
        
        # Scroll down to load all elements
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(2)
        
        # Extract product details
        product_name = "NVIDIA GeForce RTX 5090 32GB GDDR7 Graphics Card"
        manufacturer = "NVIDIA"
        
        # Get the page source and parse with BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Check if product exists in database, if not, create it
        product = session.query(Product).filter_by(url=url).first()
        if not product:
            try:
                # Extract product description
                description_elem = None
                try:
                    description_elem = driver.find_element(By.CSS_SELECTOR, '.product-description')
                except NoSuchElementException:
                    # Try with BeautifulSoup if Selenium fails
                    description_elem = soup.select_one('.product-description')
                
                description = description_elem.text.strip() if description_elem else "No description available"
            except (TimeoutException, NoSuchElementException):
                description = "No description available"
                logger.warning("Could not find product description")
            
            try:
                # Extract product specifications
                specs_elem = None
                try:
                    specs_elem = driver.find_element(By.CSS_SELECTOR, '.product-specifications')
                except NoSuchElementException:
                    # Try with BeautifulSoup if Selenium fails
                    specs_elem = soup.select_one('.product-specifications')
                
                specifications = specs_elem.text.strip() if specs_elem else "No specifications available"
            except (TimeoutException, NoSuchElementException):
                specifications = "No specifications available"
                logger.warning("Could not find product specifications")
            
            # Extract UPC
            upc = None
            try:
                spec_table = driver.find_elements(By.CSS_SELECTOR, '.specs-table tr')
                for row in spec_table:
                    if 'UPC' in row.text:
                        upc = row.find_elements(By.CSS_SELECTOR, 'td')[1].text.strip()
                        break
            except Exception:
                logger.warning("Could not find UPC in specifications table")
            
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
                upc=upc,
                url=url,
                description=description,
                specifications=specifications
            )
            session.add(product)
            session.commit()
            logger.info(f"Added new product: {product_name}, UPC: {upc}")
        
        # Extract price using multiple methods
        price = None
        try:
            # First try with Selenium
            price_selectors = [
                '.priceView-customer-price span',
                '.priceView-hero-price span',
                '.price-box .price',
                '[data-testid="customer-price"]',
                '.pricing-price',
                '.salePrice',
                '.product-price'
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip()
                    # Remove currency symbol and commas, then convert to float
                    price_text = price_text.replace('$', '').replace(',', '')
                    # Use regex to extract price
                    price_match = re.search(r'([0-9]+\.?[0-9]*)', price_text)
                    if price_match:
                        price = float(price_match.group(1))
                        logger.info(f"Found price: ${price}")
                        break
                except (NoSuchElementException, ValueError):
                    continue
            
            # If still no price, try with BeautifulSoup as well
            if not price:
                logger.info("Trying BeautifulSoup to find price")
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.text.strip()
                        price_text = price_text.replace('$', '').replace(',', '')
                        price_match = re.search(r'([0-9]+\.?[0-9]*)', price_text)
                        if price_match:
                            price = float(price_match.group(1))
                            logger.info(f"Found price with BeautifulSoup: ${price}")
                            break
                
                # Last resort - look for any price pattern in the page
                if not price:
                    price_patterns = [
                        r'\$([0-9,]+\.?[0-9]*)',  # $1,999.99 format
                        r'price["\']?\s*:\s*["\']?([0-9.]+)'  # price: 1999.99 in JS
                    ]
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, driver.page_source)
                        if matches:
                            try:
                                price = float(matches[0].replace(',', ''))
                                logger.info(f"Found price with regex: ${price}")
                                break
                            except ValueError:
                                continue
        
        except Exception as e:
            logger.error(f"Error extracting price: {e}")
        
        # Extract stock status using multiple methods
        in_stock = False
        
        try:
            # Method 1: Check for add to cart button with Selenium
            try:
                add_button = driver.find_element(By.CSS_SELECTOR, 'button[data-button-state="ADD_TO_CART"]')
                if add_button.is_displayed() and add_button.is_enabled():
                    in_stock = True
                    logger.info("Product is in stock based on add to cart button")
            except NoSuchElementException:
                pass
            
            # Method 2: Check for add to cart button with BeautifulSoup
            if not in_stock:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                add_button = soup.select_one('button[data-button-state="ADD_TO_CART"]')
                if add_button and 'disabled' not in add_button.get('class', []):
                    in_stock = True
                    logger.info("Product is in stock based on BeautifulSoup add to cart button")
            
            # Method 3: Check for sold out or unavailable text
            if not in_stock:
                sold_out_indicators = [
                    'Sold Out',
                    'Out of Stock',
                    'Coming Soon',
                    'No Longer Available'
                ]
                
                availability_selectors = [
                    '.fulfillment-add-to-cart-button', 
                    '.availability', 
                    '.fulfillment-fulfillment-summary',
                    '.fulfillment-add-to-cart'
                ]
                
                for selector in availability_selectors:
                    try:
                        availability_elem = driver.find_element(By.CSS_SELECTOR, selector)
                        availability_text = availability_elem.text
                        if not any(indicator in availability_text for indicator in sold_out_indicators):
                            in_stock = True
                            logger.info(f"Product is in stock based on availability text: {availability_text}")
                            break
                        else:
                            logger.info(f"Product is out of stock. Text: {availability_text}")
                    except NoSuchElementException:
                        continue
            
            # Method 4: Look for "In Stock" text anywhere on the page
            if not in_stock:
                if "in stock" in driver.page_source.lower():
                    in_stock = True
                    logger.info("Product is in stock based on 'in stock' text in page source")
        
        except Exception as e:
            logger.error(f"Error extracting stock status: {e}")
        
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
        logger.error(f"Error scraping Best Buy with Selenium: {e}")
        return None, None, False
    
    finally:
        # Clean up WebDriver
        if driver:
            try:
                driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
