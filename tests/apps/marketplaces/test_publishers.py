"""
Tests for marketplace publishers using Strategy pattern
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest


class TestMarketplacePublisherInterface:
    """Test the abstract interface"""

    def test_interface_cannot_be_instantiated(self):
        """Test that abstract interface cannot be instantiated"""
        # Import here to avoid Django model loading issues
        from src.apps.marketplaces.services import MarketplacePublisherInterface

        with pytest.raises(TypeError):
            MarketplacePublisherInterface()


class TestMercadoLibrePublisher:
    """Test MercadoLibre publisher implementation"""

    def setup_method(self):
        """Setup test data"""
        # Import here to avoid Django model loading issues
        from src.apps.marketplaces.services import MercadoLibrePublisher

        self.credentials = Mock()
        self.publisher = MercadoLibrePublisher(self.credentials)
        self.product = Mock()
        self.product.id = 1
        self.product.title = "Test Product"
        self.product.description = "Test description"
        self.product.ai_description = "Enhanced AI description"
        self.product.price = Decimal("99.99")
        self.product.stock = 10

    def test_publisher_implements_interface(self):
        """Test that publisher implements the interface"""
        from src.apps.marketplaces.services import MarketplacePublisherInterface

        assert isinstance(self.publisher, MarketplacePublisherInterface)

    def test_get_marketplace_name(self):
        """Test marketplace name"""
        assert self.publisher.get_marketplace_name() == "MercadoLibre"

    def test_publish_product_success(self):
        """Test successful product publishing"""
        result = self.publisher.publish_product(self.product)

        assert result["success"] is True
        assert result["marketplace_name"] == "MercadoLibre"
        assert result["marketplace_id"] == "MLM1"
        assert "details" in result
        assert "listing_url" in result["details"]

    def test_publish_product_with_exception(self):
        """Test product publishing with exception"""
        # Mock product to raise exception by making price conversion fail
        self.product.price = (
            "invalid_price"  # This will cause an error when converting to float
        )

        result = self.publisher.publish_product(self.product)

        assert result["success"] is False
        assert "MercadoLibre publishing failed" in result["error"]
        assert result["error_code"] == "ML_PUBLISH_ERROR"
        assert result["marketplace_name"] == "MercadoLibre"


class TestWalmartPublisher:
    """Test Walmart publisher implementation"""

    def setup_method(self):
        """Setup test data"""
        # Import here to avoid Django model loading issues
        from src.apps.marketplaces.services import WalmartPublisher

        self.credentials = Mock()
        self.publisher = WalmartPublisher(self.credentials)
        self.product = Mock()
        self.product.id = 2
        self.product.title = "Walmart Product"
        self.product.description = "Walmart description"
        self.product.ai_description = "Enhanced Walmart description"
        self.product.price = Decimal("199.99")
        self.product.stock = 5
        self.product.sku = "WM-001"
        self.product.weight = Decimal("2.5")
        self.product.dimensions = "15x10x5"

    def test_publisher_implements_interface(self):
        """Test that publisher implements the interface"""
        from src.apps.marketplaces.services import MarketplacePublisherInterface

        assert isinstance(self.publisher, MarketplacePublisherInterface)

    def test_get_marketplace_name(self):
        """Test marketplace name"""
        assert self.publisher.get_marketplace_name() == "Walmart"

    def test_publish_product_success(self):
        """Test successful product publishing"""
        result = self.publisher.publish_product(self.product)

        assert result["success"] is True
        assert result["marketplace_name"] == "Walmart"
        assert result["marketplace_id"] == "WM2"
        assert "details" in result
        assert "listing_url" in result["details"]

    def test_publish_product_with_exception(self):
        """Test product publishing with exception"""
        # Mock product to raise exception
        self.product.price = None  # This will cause an error

        result = self.publisher.publish_product(self.product)

        assert result["success"] is False
        assert "Walmart publishing failed" in result["error"]
        assert result["error_code"] == "WM_PUBLISH_ERROR"
        assert result["marketplace_name"] == "Walmart"


class TestParisPublisher:
    """Test Paris publisher implementation"""

    def setup_method(self):
        """Setup test data"""
        # Import here to avoid Django model loading issues
        from src.apps.marketplaces.services import ParisPublisher

        self.credentials = Mock()
        self.publisher = ParisPublisher(self.credentials)
        self.product = Mock()
        self.product.id = 3
        self.product.title = "Paris Product"
        self.product.description = "Paris description"
        self.product.ai_description = "Enhanced Paris description"
        self.product.price = Decimal("299.99")
        self.product.stock = 8
        self.product.sku = "PR-001"

    def test_publisher_implements_interface(self):
        """Test that publisher implements the interface"""
        from src.apps.marketplaces.services import MarketplacePublisherInterface

        assert isinstance(self.publisher, MarketplacePublisherInterface)

    def test_get_marketplace_name(self):
        """Test marketplace name"""
        assert self.publisher.get_marketplace_name() == "Paris"

    def test_publish_product_success(self):
        """Test successful product publishing"""
        result = self.publisher.publish_product(self.product)

        assert result["success"] is True
        assert result["marketplace_name"] == "Paris"
        assert result["marketplace_id"] == "PR3"
        assert "details" in result
        assert "listing_url" in result["details"]

    def test_publish_product_with_exception(self):
        """Test product publishing with exception"""
        # Mock product to raise exception by making price conversion fail
        self.product.price = (
            "invalid_price"  # This will cause an error when converting to float
        )

        result = self.publisher.publish_product(self.product)

        assert result["success"] is False
        assert "Paris publishing failed" in result["error"]
        assert result["error_code"] == "PR_PUBLISH_ERROR"
        assert result["marketplace_name"] == "Paris"


class TestMarketplacePublisherFactory:
    """Test the factory for creating publishers"""

    def test_create_mercadolibre_publisher(self):
        """Test creating MercadoLibre publisher"""
        from src.apps.marketplaces.services import (
            MarketplacePublisherFactory,
            MercadoLibrePublisher,
        )

        credentials = Mock()
        publisher = MarketplacePublisherFactory.create_publisher(
            "mercadolibre", credentials
        )

        assert isinstance(publisher, MercadoLibrePublisher)
        assert publisher.get_marketplace_name() == "MercadoLibre"

    def test_create_walmart_publisher(self):
        """Test creating Walmart publisher"""
        from src.apps.marketplaces.services import (
            MarketplacePublisherFactory,
            WalmartPublisher,
        )

        credentials = Mock()
        publisher = MarketplacePublisherFactory.create_publisher("walmart", credentials)

        assert isinstance(publisher, WalmartPublisher)
        assert publisher.get_marketplace_name() == "Walmart"

    def test_create_paris_publisher(self):
        """Test creating Paris publisher"""
        from src.apps.marketplaces.services import (
            MarketplacePublisherFactory,
            ParisPublisher,
        )

        credentials = Mock()
        publisher = MarketplacePublisherFactory.create_publisher("paris", credentials)

        assert isinstance(publisher, ParisPublisher)
        assert publisher.get_marketplace_name() == "Paris"

    def test_create_unsupported_marketplace(self):
        """Test creating publisher for unsupported marketplace"""
        from src.apps.marketplaces.services import MarketplacePublisherFactory

        credentials = Mock()

        with pytest.raises(ValueError, match="Unsupported marketplace: amazon"):
            MarketplacePublisherFactory.create_publisher("amazon", credentials)

    def test_create_publisher_case_insensitive(self):
        """Test that marketplace slug is case insensitive"""
        from src.apps.marketplaces.services import (
            MarketplacePublisherFactory,
            MercadoLibrePublisher,
            WalmartPublisher,
        )

        credentials = Mock()

        # Test uppercase
        publisher = MarketplacePublisherFactory.create_publisher(
            "MERCADOLIBRE", credentials
        )
        assert isinstance(publisher, MercadoLibrePublisher)

        # Test mixed case
        publisher = MarketplacePublisherFactory.create_publisher("WaLmArT", credentials)
        assert isinstance(publisher, WalmartPublisher)


class TestMarketplacePublisher:
    """Test the main marketplace publisher service"""

    def setup_method(self):
        """Setup test data"""
        # Import here to avoid Django model loading issues
        from src.apps.marketplaces.services import MarketplacePublisher

        self.marketplace = Mock()
        self.marketplace.slug = "mercadolibre"
        self.marketplace.id = 1
        self.marketplace.name = "MercadoLibre"

        self.credentials = Mock()
        self.marketplace.marketplacecredential = self.credentials

        self.publisher = MarketplacePublisher(self.marketplace)

        self.product = Mock()
        self.product.id = 1
        self.product.title = "Test Product"
        self.product.description = "Test description"
        self.product.ai_description = "Enhanced AI description"
        self.product.price = Decimal("99.99")
        self.product.stock = 10

    @patch(
        "src.apps.marketplaces.services.MarketplacePublisherFactory.create_publisher"
    )
    def test_publish_product_success(self, mock_factory):
        """Test successful product publishing"""
        # Mock the factory to return a successful publisher
        mock_publisher = Mock()
        mock_publisher.publish_product.return_value = {
            "success": True,
            "marketplace_id": "MLM123",
            "marketplace_name": "MercadoLibre",
        }
        mock_factory.return_value = mock_publisher

        result = self.publisher.publish_product(self.product)

        # Verify factory was called
        mock_factory.assert_called_once_with("mercadolibre", self.credentials)

        # Verify result
        assert result["success"] is True
        assert (
            result["marketplace_id"] == "MLM123"
        )  # This is the marketplace-specific ID
        assert result["marketplace_name"] == "MercadoLibre"
        assert result["marketplace_slug"] == "mercadolibre"
        assert (
            result["internal_marketplace_id"] == 1
        )  # This is the internal marketplace ID

    @patch(
        "src.apps.marketplaces.services.MarketplacePublisherFactory.create_publisher"
    )
    def test_publish_product_failure(self, mock_factory):
        """Test product publishing failure"""
        # Mock the factory to return a failed publisher
        mock_publisher = Mock()
        mock_publisher.publish_product.return_value = {
            "success": False,
            "error": "API rate limit exceeded",
            "error_code": "RATE_LIMIT",
        }
        mock_factory.return_value = mock_publisher

        result = self.publisher.publish_product(self.product)

        # Verify result
        assert result["success"] is False
        assert result["error"] == "API rate limit exceeded"
        assert result["error_code"] == "RATE_LIMIT"
        assert result["marketplace_slug"] == "mercadolibre"
        assert result["internal_marketplace_id"] == 1

    @patch(
        "src.apps.marketplaces.services.MarketplacePublisherFactory.create_publisher"
    )
    def test_publish_product_exception(self, mock_factory):
        """Test product publishing with exception"""
        # Mock the factory to raise an exception
        mock_factory.side_effect = Exception("Factory error")

        result = self.publisher.publish_product(self.product)

        # Verify result
        assert result["success"] is False
        assert "Marketplace publishing failed" in result["error"]
        assert result["error_code"] == "GENERAL_PUBLISH_ERROR"
        assert result["marketplace_slug"] == "mercadolibre"
        assert result["internal_marketplace_id"] == 1


class TestMarketplacePublisherIntegration:
    """Integration tests for marketplace publishers"""

    def test_all_publishers_implement_interface(self):
        """Test that all concrete publishers implement the interface"""
        from src.apps.marketplaces.services import (
            MarketplacePublisherInterface,
            MercadoLibrePublisher,
            ParisPublisher,
            WalmartPublisher,
        )

        credentials = Mock()

        publishers = [
            MercadoLibrePublisher(credentials),
            WalmartPublisher(credentials),
            ParisPublisher(credentials),
        ]

        for publisher in publishers:
            assert isinstance(publisher, MarketplacePublisherInterface)
            assert hasattr(publisher, "publish_product")
            assert hasattr(publisher, "get_marketplace_name")

    def test_publisher_factory_creates_correct_types(self):
        """Test that factory creates correct publisher types"""
        from src.apps.marketplaces.services import (
            MarketplacePublisherFactory,
            MercadoLibrePublisher,
            ParisPublisher,
            WalmartPublisher,
        )

        credentials = Mock()

        # Test all supported marketplaces
        test_cases = [
            ("mercadolibre", MercadoLibrePublisher),
            ("walmart", WalmartPublisher),
            ("paris", ParisPublisher),
        ]

        for slug, expected_class in test_cases:
            publisher = MarketplacePublisherFactory.create_publisher(slug, credentials)
            assert isinstance(publisher, expected_class)
            assert (
                publisher.get_marketplace_name()
                == expected_class(credentials).get_marketplace_name()
            )
