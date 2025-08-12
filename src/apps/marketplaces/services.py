"""
Services for marketplace integration using Strategy pattern
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from django.conf import settings


class MarketplacePublisherInterface(ABC):
    """
    Abstract interface for marketplace publishers
    """

    @abstractmethod
    def publish_product(self, product) -> Dict[str, Any]:
        """
        Publish a product to the marketplace
        Returns: Dict with 'success' boolean and additional data
        """
        pass

    @abstractmethod
    def get_marketplace_name(self) -> str:
        """Get the name of the marketplace"""
        pass


class MercadoLibrePublisher(MarketplacePublisherInterface):
    """
    MercadoLibre marketplace publisher implementation
    """

    def __init__(self, credentials):
        self.credentials = credentials
        self.api_url = "https://api.mercadolibre.com"

    def publish_product(self, product) -> Dict[str, Any]:
        """
        Publish to MercadoLibre
        """
        try:
            # Prepare product data for MercadoLibre
            data = {
                "title": product.title,
                "description": product.ai_description or product.description,
                "price": float(product.price),
                "available_quantity": product.stock,
                "category_id": "MLM1051",  # Example category ID
                "condition": "new",
                "currency_id": "ARS",
                "listing_type_id": "gold_special",
            }

            # Here would go the actual API call to MercadoLibre
            # For now, return mock success response
            return {
                "success": True,
                "marketplace_id": f"MLM{product.id}",
                "marketplace_name": "MercadoLibre",
                "details": {
                    "api_response": "Product published successfully",
                    "listing_url": f"https://articulo.mercadolibre.com.ar/{product.id}",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"MercadoLibre publishing failed: {str(e)}",
                "error_code": "ML_PUBLISH_ERROR",
                "marketplace_name": "MercadoLibre",
            }

    def get_marketplace_name(self) -> str:
        return "MercadoLibre"


class WalmartPublisher(MarketplacePublisherInterface):
    """
    Walmart marketplace publisher implementation
    """

    def __init__(self, credentials):
        self.credentials = credentials
        self.api_url = "https://marketplace.walmartapis.com"

    def publish_product(self, product) -> Dict[str, Any]:
        """
        Publish to Walmart
        """
        try:
            # Prepare product data for Walmart
            data = {
                "productName": product.title,
                "shortDescription": product.ai_description or product.description,
                "price": {"amount": float(product.price), "currency": "USD"},
                "quantity": product.stock,
                "sku": product.sku,
                "brand": "Generic",
                "shipping": {
                    "weight": float(product.weight or 1.0),
                    "dimensions": product.dimensions or "10x10x10",
                },
            }

            # Here would go the actual API call to Walmart
            # For now, return mock success response
            return {
                "success": True,
                "marketplace_id": f"WM{product.id}",
                "marketplace_name": "Walmart",
                "details": {
                    "api_response": "Product published successfully",
                    "listing_url": f"https://walmart.com/item/{product.id}",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Walmart publishing failed: {str(e)}",
                "error_code": "WM_PUBLISH_ERROR",
                "marketplace_name": "Walmart",
            }

    def get_marketplace_name(self) -> str:
        return "Walmart"


class ParisPublisher(MarketplacePublisherInterface):
    """
    Paris marketplace publisher implementation
    """

    def __init__(self, credentials):
        self.credentials = credentials
        self.api_url = "https://api.paris.cl"

    def publish_product(self, product) -> Dict[str, Any]:
        """
        Publish to Paris
        """
        try:
            # Prepare product data for Paris
            data = {
                "nombre": product.title,
                "descripcion": product.ai_description or product.description,
                "precio": float(product.price),
                "stock": product.stock,
                "codigo": product.sku,
                "categoria": "Electrónicos",
                "marca": "Generic",
            }

            # Here would go the actual API call to Paris
            # For now, return mock success response
            return {
                "success": True,
                "marketplace_id": f"PR{product.id}",
                "marketplace_name": "Paris",
                "details": {
                    "api_response": "Product published successfully",
                    "listing_url": f"https://paris.cl/producto/{product.id}",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Paris publishing failed: {str(e)}",
                "error_code": "PR_PUBLISH_ERROR",
                "marketplace_name": "Paris",
            }

    def get_marketplace_name(self) -> str:
        return "Paris"


class MarketplacePublisherFactory:
    """
    Factory for creating marketplace publishers
    """

    @staticmethod
    def create_publisher(
        marketplace_slug: str, credentials
    ) -> MarketplacePublisherInterface:
        """
        Create a publisher instance based on marketplace slug
        """
        publishers = {
            "mercadolibre": MercadoLibrePublisher,
            "walmart": WalmartPublisher,
            "paris": ParisPublisher,
        }

        publisher_class = publishers.get(marketplace_slug.lower())
        if not publisher_class:
            raise ValueError(f"Unsupported marketplace: {marketplace_slug}")

        return publisher_class(credentials)


class MarketplacePublisher:
    """
    Main marketplace publisher service that uses the factory pattern
    """

    def __init__(self, marketplace):
        self.marketplace = marketplace
        self.credentials = marketplace.marketplacecredential

    def publish_product(self, product):
        """
        Publish a product to the marketplace using the appropriate publisher
        """
        try:
            # Create the appropriate publisher using the factory
            publisher = MarketplacePublisherFactory.create_publisher(
                self.marketplace.slug, self.credentials
            )

            # Publish the product
            result = publisher.publish_product(product)

            # Add marketplace information to the result
            result["marketplace_slug"] = self.marketplace.slug
            result["internal_marketplace_id"] = self.marketplace.id

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Marketplace publishing failed: {str(e)}",
                "error_code": "GENERAL_PUBLISH_ERROR",
                "marketplace_slug": self.marketplace.slug,
                "internal_marketplace_id": self.marketplace.id,
            }
