"""
Configure pytest for RTX 5090 Stock Tracker tests
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

# Add the project root to the path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Fixtures for common test objects
@pytest.fixture
def mock_session():
    """Create a mock database session"""
    session = MagicMock()
    return session

@pytest.fixture
def mock_retailer():
    """Create a mock retailer object"""
    from database.models import Retailer
    retailer = MagicMock(spec=Retailer)
    retailer.id = 1
    retailer.name = "Newegg"
    retailer.website = "https://www.newegg.com"
    return retailer

@pytest.fixture
def sample_html_path(request):
    """Return the path to the fixtures directory"""
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'scrapers', 'fixtures')
    return lambda filename: os.path.join(fixtures_dir, filename)