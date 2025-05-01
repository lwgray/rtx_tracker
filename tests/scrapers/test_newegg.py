"""
Unit tests for Newegg scraper
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import requests
import os
import sys
import json
from bs4 import BeautifulSoup

# Add the project root to path to ensure imports work properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from scrapers.newegg import scrape_newegg, get_headers
from database.models import Product, PriceHistory, StockHistory, Retailer


class TestNeweggScraper(unittest.TestCase):
    """Test cases for the Newegg scraper module"""

    def setUp(self):
        """Set up test fixtures, if any."""
        # Create a mock retailer
        self.mock_retailer = Mock(spec=Retailer)
        self.mock_retailer.id = 1
        self.mock_retailer.name = "Newegg"
        self.mock_retailer.website = "https://www.newegg.com"

        # Mock the database session
        self.mock_session = MagicMock()

        # Path to sample HTML files for testing
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        os.makedirs(self.fixtures_dir, exist_ok=True)

    def test_get_headers(self):
        """Test the get_headers function returns the expected headers."""
        headers = get_headers()
        self.assertIsInstance(headers, dict)
        self.assertIn('User-Agent', headers)
        self.assertIn('Accept-Language', headers)
        self.assertIn('Accept-Encoding', headers)
        self.assertIn('Connection', headers)
        self.assertIn('Referer', headers)
        
        # Verify the User-Agent looks like a real browser
        self.assertIn('Mozilla', headers['User-Agent'])
        self.assertIn('Chrome', headers['User-Agent'])

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')  # Mock sleep to speed up tests
    def test_scrape_newegg_success(self, mock_sleep, mock_get):
        """Test successful scraping with mock product listing page."""
        # Load sample HTML from a fixture file
        fixture_path = os.path.join(self.fixtures_dir, 'newegg_listing.html')
        
        # If the fixture doesn't exist, create a simplified one for testing
        if not os.path.exists(fixture_path):
            with open(fixture_path, 'w', encoding='utf-8') as f:
                f.write('''
                <html>
                <body>
                    <div class="item-cells-wrap">
                        <div class="item-cell">
                            <div class="item-container">
                                <a href="https://www.newegg.com/p/N82E16814137802" class="item-title">
                                    MSI Gaming GeForce RTX 5090 24GB GDDR7 PCI Express 5.0 Video Card
                                </a>
                                <div class="price-current">
                                    <span>$</span><strong>1,999</strong><sup>.99</sup>
                                </div>
                                <p class="item-promo">In Stock</p>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                ''')
        
        # Create a mock product details response
        mock_product_details = '''
        <html>
        <body>
            <div class="product-description">
                <p>The MSI GeForce RTX 5090 is the most powerful GPU on the market, featuring 32GB of GDDR7 memory.</p>
            </div>
            <div id="Specifications">
                <table>
                    <tr>
                        <th>UPC</th>
                        <td>123456789012</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock response for the listing page
        with open(fixture_path, 'r', encoding='utf-8') as f:
            mock_listing_response = MagicMock()
            mock_listing_response.status_code = 200
            mock_listing_response.content = f.read().encode('utf-8')
        
        # Configure the mock response for the product details page
        mock_product_response = MagicMock()
        mock_product_response.status_code = 200
        mock_product_response.content = mock_product_details.encode('utf-8')
        
        # Configure the mock to return different responses based on the URL
        mock_get.side_effect = lambda url, headers, timeout: (
            mock_listing_response if "rtx+5090" in url else mock_product_response
        )
        
        # Configure the mock session to handle product queries
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # Verify the results
        self.assertTrue(len(results) > 0)
        
        # Check that the session was used correctly
        self.mock_session.add.assert_called()
        self.mock_session.commit.assert_called()
        
        # Check the first result
        product, price, in_stock = results[0]
        self.assertIsNotNone(product)
        self.assertIsNotNone(price)
        self.assertTrue(in_stock)  # Should be in stock based on the fixture

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')
    def test_scrape_newegg_http_error(self, mock_sleep, mock_get):
        """Test behavior when Newegg returns an HTTP error."""
        # Configure the mock to return an error response
        mock_response = MagicMock()
        mock_response.status_code = 403  # Forbidden
        mock_get.return_value = mock_response
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # Verify the results
        self.assertEqual(len(results), 0)  # Should return empty list on error
        
        # Verify that the request was attempted
        mock_get.assert_called_once()
        
        # Verify that no session operations were performed
        self.mock_session.add.assert_not_called()

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')
    def test_scrape_newegg_no_products_found(self, mock_sleep, mock_get):
        """Test behavior when no products match the search criteria."""
        # Create a mock HTML with no matching products
        mock_html = '''
        <html>
        <body>
            <div class="item-cells-wrap">
                <!-- No products with RTX 5090 in the name -->
                <div class="item-cell">
                    <div class="item-container">
                        <a href="#" class="item-title">
                            MSI Gaming GeForce RTX 4090 24GB GDDR6X PCI Express 4.0 Video Card
                        </a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        mock_get.return_value = mock_response
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # Verify the results
        self.assertEqual(len(results), 0)  # Should return empty list when no matching products

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')
    def test_scrape_newegg_existing_product(self, mock_sleep, mock_get):
        """Test behavior when a product already exists in the database."""
        # Create a mock HTML with a product
        mock_html = '''
        <html>
        <body>
            <div class="item-cells-wrap">
                <div class="item-cell">
                    <div class="item-container">
                        <a href="https://www.newegg.com/p/N82E16814137802" class="item-title">
                            MSI Gaming GeForce RTX 5090 24GB GDDR7 PCI Express 5.0 Video Card
                        </a>
                        <div class="price-current">
                            <span>$</span><strong>1,999</strong><sup>.99</sup>
                        </div>
                        <p class="item-promo">In Stock</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        mock_get.return_value = mock_response
        
        # Create a mock existing product
        mock_product = MagicMock(spec=Product)
        mock_product.id = 1
        mock_product.name = "MSI Gaming GeForce RTX 5090 24GB GDDR7 PCI Express 5.0 Video Card"
        mock_product.url = "https://www.newegg.com/p/N82E16814137802"
        
        # Configure the session to return the existing product
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_product
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # Verify the results
        self.assertEqual(len(results), 1)
        product, price, in_stock = results[0]
        self.assertEqual(product.id, 1)  # Should be the existing product
        
        # Verify that add was called for price history and stock history
        self.assertEqual(self.mock_session.add.call_count, 2)

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')
    def test_scrape_newegg_out_of_stock(self, mock_sleep, mock_get):
        """Test behavior when a product is out of stock."""
        # Create a mock HTML with an out-of-stock product
        mock_html = '''
        <html>
        <body>
            <div class="item-cells-wrap">
                <div class="item-cell">
                    <div class="item-container">
                        <a href="https://www.newegg.com/p/N82E16814137803" class="item-title">
                            ASUS ROG Strix GeForce RTX 5090 32GB GDDR7 PCI Express 5.0 Video Card
                        </a>
                        <div class="price-current">
                            <span>$</span><strong>2,499</strong><sup>.99</sup>
                        </div>
                        <p class="item-promo item-info-stock-out">OUT OF STOCK</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        mock_get.return_value = mock_response
        
        # Configure the session to not find an existing product
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Create a mock product details response
        mock_product_details = '''
        <html>
        <body>
            <div class="product-description">
                <p>The ASUS ROG Strix GeForce RTX 5090 is the most powerful GPU on the market.</p>
            </div>
            <div id="Specifications">
                <table>
                    <tr>
                        <th>UPC</th>
                        <td>987654321098</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock product response
        mock_product_response = MagicMock()
        mock_product_response.status_code = 200
        mock_product_response.content = mock_product_details.encode('utf-8')
        
        # Configure the mock to return different responses based on the URL
        mock_get.side_effect = lambda url, headers, timeout: (
            mock_response if "rtx+5090" in url else mock_product_response
        )
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # Verify the results
        self.assertEqual(len(results), 1)
        product, price, in_stock = results[0]
        self.assertFalse(in_stock)  # Should be out of stock

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')
    def test_scrape_newegg_alternative_selectors(self, mock_sleep, mock_get):
        """Test behavior when the HTML structure uses alternative CSS selectors."""
        # Create a mock HTML with alternative selectors
        mock_html = '''
        <html>
        <body>
            <div class="product-listing">
                <div class="product-item">
                    <div class="product-info">
                        <a href="https://www.newegg.com/p/N82E16814137804" class="product-title">
                            GIGABYTE AORUS GeForce RTX 5090 32GB GDDR7 PCI Express 5.0 Video Card
                        </a>
                        <div class="product-price">
                            <span class="price-current">$2,199.99</span>
                        </div>
                        <div class="product-stock">In Stock</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        
        # Create a mock product details response
        mock_product_details = '''
        <html>
        <body>
            <div class="details">
                <p>The GIGABYTE AORUS GeForce RTX 5090 features advanced cooling and RGB lighting.</p>
            </div>
            <div class="specifications">
                <table>
                    <tr>
                        <th>UPC</th>
                        <td>456789012345</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock product response
        mock_product_response = MagicMock()
        mock_product_response.status_code = 200
        mock_product_response.content = mock_product_details.encode('utf-8')
        
        # Configure the mock to return different responses based on the URL
        mock_get.side_effect = lambda url, headers, timeout: (
            mock_response if "rtx+5090" in url else mock_product_response
        )
        
        # Configure the session to not find an existing product
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # Verify the results
        self.assertEqual(len(results), 1)
        product, price, in_stock = results[0]
        self.assertEqual(product.name, "GIGABYTE AORUS GeForce RTX 5090 32GB GDDR7 PCI Express 5.0 Video Card")
        self.assertEqual(price, 2199.99)
        self.assertTrue(in_stock)

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')
    def test_scrape_newegg_error_handling(self, mock_sleep, mock_get):
        """Test error handling in the scraper."""
        # Configure the mock to raise an exception
        mock_get.side_effect = requests.RequestException("Simulated network error")
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # Verify the results
        self.assertEqual(len(results), 0)  # Should return empty list on error
        
        # Verify that no session operations were performed
        self.mock_session.add.assert_not_called()

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')
    def test_scrape_newegg_product_page_error(self, mock_sleep, mock_get):
        """Test behavior when the product page returns an error."""
        # Create a mock HTML with a product
        mock_listing_html = '''
        <html>
        <body>
            <div class="item-cells-wrap">
                <div class="item-cell">
                    <div class="item-container">
                        <a href="https://www.newegg.com/p/N82E16814137805" class="item-title">
                            ZOTAC Gaming GeForce RTX 5090 32GB GDDR7 PCI Express 5.0 Video Card
                        </a>
                        <div class="price-current">
                            <span>$</span><strong>2,099</strong><sup>.99</sup>
                        </div>
                        <p class="item-promo">In Stock</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock listing response
        mock_listing_response = MagicMock()
        mock_listing_response.status_code = 200
        mock_listing_response.content = mock_listing_html.encode('utf-8')
        
        # Configure the mock product response to return an error
        mock_product_response = MagicMock()
        mock_product_response.status_code = 404  # Not Found
        
        # Configure the mock to return different responses based on the URL
        def mock_get_side_effect(url, headers, timeout):
            if "rtx+5090" in url:
                return mock_listing_response
            else:
                # This simulates an error on the product page
                return mock_product_response
        
        mock_get.side_effect = mock_get_side_effect
        
        # Configure the session to not find an existing product
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # The scraper should still create a product with default description and specs
        self.assertEqual(len(results), 1)
        product, price, in_stock = results[0]
        self.assertEqual(product.description, "No description available")
        self.assertEqual(product.specifications, "No specifications available")

    @patch('scrapers.newegg.requests.get')
    @patch('scrapers.newegg.time.sleep')
    def test_manufacturer_detection(self, mock_sleep, mock_get):
        """Test detection of manufacturers from product names."""
        # Create a mock HTML with products from different manufacturers
        mock_html = '''
        <html>
        <body>
            <div class="item-cells-wrap">
                <div class="item-cell">
                    <a href="https://www.newegg.com/p/1" class="item-title">
                        ASUS TUF Gaming GeForce RTX 5090 32GB GDDR7
                    </a>
                    <div class="price-current"><strong>2099</strong></div>
                </div>
                <div class="item-cell">
                    <a href="https://www.newegg.com/p/2" class="item-title">
                        MSI Ventus GeForce RTX 5090 32GB GDDR7
                    </a>
                    <div class="price-current"><strong>2199</strong></div>
                </div>
                <div class="item-cell">
                    <a href="https://www.newegg.com/p/3" class="item-title">
                        GIGABYTE AORUS GeForce RTX 5090 32GB GDDR7
                    </a>
                    <div class="price-current"><strong>2299</strong></div>
                </div>
                <div class="item-cell">
                    <a href="https://www.newegg.com/p/4" class="item-title">
                        EVGA FTW3 GeForce RTX 5090 32GB GDDR7
                    </a>
                    <div class="price-current"><strong>2399</strong></div>
                </div>
                <div class="item-cell">
                    <a href="https://www.newegg.com/p/5" class="item-title">
                        ZOTAC Gaming GeForce RTX 5090 32GB GDDR7
                    </a>
                    <div class="price-current"><strong>2499</strong></div>
                </div>
                <div class="item-cell">
                    <a href="https://www.newegg.com/p/6" class="item-title">
                        NVIDIA GeForce RTX 5090 Founders Edition 32GB GDDR7
                    </a>
                    <div class="price-current"><strong>1999</strong></div>
                </div>
                <div class="item-cell">
                    <a href="https://www.newegg.com/p/7" class="item-title">
                        PNY GeForce RTX 5090 32GB GDDR7
                    </a>
                    <div class="price-current"><strong>2099</strong></div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        mock_get.return_value = mock_response
        
        # Create a basic product details response
        mock_product_details = '<html><body><div class="description">Test</div></body></html>'
        mock_product_response = MagicMock()
        mock_product_response.status_code = 200
        mock_product_response.content = mock_product_details.encode('utf-8')
        
        # Configure the mock to return different responses
        def side_effect(url, headers, timeout):
            if "rtx+5090" in url:
                return mock_response
            else:
                return mock_product_response
        
        mock_get.side_effect = side_effect
        
        # Mock the product query to always return None (new products)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Store the products added to the session
        products = []
        
        def capture_product(product):
            if isinstance(product, Product):
                products.append(product)
        
        # Override the add method to capture products
        self.mock_session.add.side_effect = capture_product
        
        # Call the scrape_newegg function
        results = scrape_newegg(self.mock_session, self.mock_retailer)
        
        # Verify the results
        self.assertEqual(len(results), 7)  # 7 products in the mock HTML
        
        # Verify manufacturer detection
        manufacturers = [p.manufacturer for p in products]
        self.assertIn("ASUS", manufacturers)
        self.assertIn("MSI", manufacturers)
        self.assertIn("GIGABYTE", manufacturers)
        self.assertIn("EVGA", manufacturers)
        self.assertIn("ZOTAC", manufacturers)
        self.assertIn("NVIDIA", manufacturers)
        
        # The last one should be "Unknown" since PNY is not in the detection code
        self.assertIn("Unknown", manufacturers)


if __name__ == '__main__':
    unittest.main()
