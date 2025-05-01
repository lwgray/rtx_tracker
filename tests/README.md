# RTX 5090 Stock Tracker - Test Suite

This directory contains tests for the RTX 5090 Stock Tracker application.

## Running Tests

You can run all tests with the following command from the project root:

```bash
python -m unittest discover -s tests
```

To run specific test files:

```bash
python -m unittest tests/scrapers/test_newegg.py
```

To run a specific test case:

```bash
python -m unittest tests.scrapers.test_newegg.TestNeweggScraper.test_scrape_newegg_success
```

## Test Structure

- `tests/scrapers/` - Tests for web scrapers
  - `test_newegg.py` - Tests for the Newegg scraper
  - `fixtures/` - HTML fixtures for scraper tests

## Test Fixtures

The `fixtures` directory contains sample HTML files used for testing the scrapers. These files simulate the responses from the retailers' websites, allowing us to test the scraper's functionality without making actual HTTP requests.

## Adding New Tests

When adding new tests:

1. Follow the naming convention `test_*.py` for test files
2. Create test classes that inherit from `unittest.TestCase`
3. Create test methods that start with `test_`
4. Use appropriate assertions to verify the behavior of the code

## Mock Objects

The tests use Python's `unittest.mock` module to mock external dependencies like HTTP requests. This allows us to test the scrapers' logic without actually making network requests, which would make the tests slow, flaky, and dependent on external services.

Examples of mocked objects:
- HTTP responses from retailers
- Database sessions
- Time delays (sleep)

## Code Coverage

To measure code coverage, install the `coverage` package and run:

```bash
pip install coverage
coverage run -m unittest discover -s tests
coverage report
coverage html  # Generates an HTML report in htmlcov/
```