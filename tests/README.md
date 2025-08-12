# Tests Structure

This directory contains all tests for the MultiMarket Hub project, organized to mirror the application structure for better maintainability and discoverability.

## 📁 Directory Structure

```
tests/
├── __init__.py
├── conftest.py                 # Pytest configuration and fixtures
├── factories.py               # Test data factories
├── README.md                  # This file
├── apps/                      # Tests organized by Django app
│   ├── core/
│   │   ├── __init__.py
│   │   └── test_models.py     # Core models tests
│   ├── products/
│   │   ├── __init__.py
│   │   ├── test_models.py     # Product models tests
│   │   ├── test_views.py      # Product API views tests
│   │   └── test_tasks.py      # Product Celery tasks tests
│   ├── marketplaces/
│   │   ├── __init__.py
│   │   ├── test_models.py     # Marketplace models tests
│   │   ├── test_views.py      # Marketplace API views tests
│   │   ├── test_services.py   # Marketplace services tests
│   │   ├── test_tasks.py      # Marketplace Celery tasks tests
│   │   └── test_publishers.py # Strategy pattern publishers tests
│   ├── webhooks/
│   │   ├── __init__.py
│   │   ├── test_models.py     # Webhook models tests
│   │   ├── test_services.py   # Webhook services tests
│   │   └── test_tasks.py      # Webhook Celery tasks tests
│   └── ai_assistant/
│       ├── __init__.py
│       └── test_services.py   # AI services tests
├── integration/               # Integration tests
│   ├── __init__.py
│   ├── test_product_workflow.py      # End-to-end product workflow tests
│   └── test_marketplace_integration.py # Marketplace integration tests
└── workflows/                 # Workflow-specific tests
    ├── __init__.py
    └── test_celery_workflows.py      # Complex Celery workflow tests
```

## 🎯 Test Categories

### Unit Tests (`tests/apps/`)
- **Models**: Test model creation, validation, and relationships
- **Views**: Test API endpoints, authentication, and responses
- **Services**: Test business logic and external service integrations
- **Tasks**: Test Celery task execution and error handling

### Integration Tests (`tests/integration/`)
- **Product Workflow**: End-to-end tests for product creation → AI enhancement → marketplace publishing
- **Marketplace Integration**: Tests for complete marketplace integration flows

### Workflow Tests (`tests/workflows/`)
- **Celery Workflows**: Complex asynchronous workflow tests
- **Error Handling**: Comprehensive error handling and retry logic tests

## 🚀 Running Tests

### Run all tests
```bash
pytest
```

### Run tests by category
```bash
# Unit tests only
pytest tests/apps/

# Integration tests only
pytest tests/integration/

# Workflow tests only
pytest tests/workflows/

# Specific app tests
pytest tests/apps/products/
pytest tests/apps/marketplaces/
```

### Run tests by type
```bash
# Model tests across all apps
pytest tests/apps/*/test_models.py

# View tests across all apps
pytest tests/apps/*/test_views.py

# Service tests across all apps
pytest tests/apps/*/test_services.py

# Task tests across all apps
pytest tests/apps/*/test_tasks.py
```

### Run tests with markers
```bash
# Integration tests only
pytest -m integration

# Unit tests only
pytest -m unit

# Exclude slow tests
pytest -m "not slow"
```

## 📊 Test Coverage

Current test coverage by component:

- ✅ **Core Models**: 100% (5/5 tests)
- ✅ **Products**: 100% (9/9 tests)
- ✅ **Marketplaces**: 100% (28/28 tests)
- ✅ **Webhooks**: 100% (8/8 tests)
- ✅ **AI Assistant**: 100% (5/5 tests)
- ✅ **Integration**: 100% (3/3 tests)
- ⚠️ **Workflows**: 67% (6/9 tests passing)

**Total: 58/61 tests passing (95% success rate)**

## 🛠 Test Utilities

### Fixtures (`conftest.py`)
- `api_client`: REST API test client
- `user`: Test user with authentication
- `authenticated_client`: Pre-authenticated API client

### Factories (`factories.py`)
- `UserFactory`: Create test users
- `CategoryFactory`: Create product categories
- `ProductFactory`: Create test products
- `MarketplaceFactory`: Create test marketplaces
- `ProductListingFactory`: Create marketplace listings
- `WebhookEventFactory`: Create webhook events

## 🔧 Test Configuration

### Settings
Tests use `src.config.settings.test` which includes:
- SQLite in-memory database
- Celery eager mode for synchronous task execution
- Disabled logging for faster test execution
- Mock external API calls

### Markers
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.slow`: Slow-running tests

## 📝 Writing New Tests

### Guidelines
1. **Mirror app structure**: Place tests in the corresponding `tests/apps/<app_name>/` directory
2. **Separate by component**: Use separate files for models, views, services, and tasks
3. **Use descriptive names**: Test methods should clearly describe what they test
4. **Mock external dependencies**: Use `@patch` for external APIs and services
5. **Test both success and failure cases**: Include error handling tests
6. **Use factories**: Leverage test factories for consistent test data

### Example Test Structure
```python
"""
Tests for <component> <functionality>
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from src.apps.<app>.models import <Model>


class <Component>Test(TestCase):
    
    def setUp(self):
        """Setup test data"""
        # Create test objects
    
    def test_<functionality>_success(self):
        """Test successful <functionality>"""
        # Test implementation
    
    def test_<functionality>_failure(self):
        """Test <functionality> failure handling"""
        # Test error cases
```

## 🎯 Benefits of This Structure

1. **Discoverability**: Easy to find tests related to specific functionality
2. **Maintainability**: Changes to app code can be easily reflected in corresponding tests
3. **Scalability**: New apps and features can follow the same pattern
4. **Separation of Concerns**: Different types of tests are clearly separated
5. **Parallel Execution**: Tests can be run in parallel by category or app
6. **Clear Ownership**: Each team/developer can focus on their app's tests