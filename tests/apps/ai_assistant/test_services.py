"""
Tests for AI assistant services
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from src.apps.ai_assistant.services import AIProductEnhancer


class AIProductEnhancerTest(TestCase):

    @override_settings(OPENAI_API_KEY="test-api-key")
    def setUp(self):
        self.enhancer = AIProductEnhancer()

    @patch("src.apps.ai_assistant.services.LLMChain")
    def test_enhance_description_success(self, mock_chain_class):
        """Test successful description enhancement"""
        # Mock the chain
        mock_chain = MagicMock()
        mock_chain_class.return_value = mock_chain
        mock_chain.run.return_value = "Enhanced product description with AI"

        result = self.enhancer.enhance_description(
            title="iPhone 15", description="New iPhone", category="Electronics"
        )

        self.assertEqual(result, "Enhanced product description with AI")
        mock_chain.run.assert_called_once_with(
            title="iPhone 15", description="New iPhone", category="Electronics"
        )

    @patch("src.apps.ai_assistant.services.LLMChain")
    def test_enhance_description_failure(self, mock_chain_class):
        """Test description enhancement failure fallback"""
        # Mock the chain to raise an exception
        mock_chain = MagicMock()
        mock_chain_class.return_value = mock_chain
        mock_chain.run.side_effect = Exception("API Error")

        result = self.enhancer.enhance_description(
            title="iPhone 15", description="New iPhone", category="Electronics"
        )

        # Should fallback to original description
        self.assertEqual(result, "New iPhone")

    @patch("src.apps.ai_assistant.services.LLMChain")
    def test_generate_keywords_success(self, mock_chain_class):
        """Test successful keyword generation"""
        # Mock the chain
        mock_chain = MagicMock()
        mock_chain_class.return_value = mock_chain
        mock_chain.run.return_value = "iphone, smartphone, apple, mobile, technology"

        result = self.enhancer.generate_keywords(
            title="iPhone 15",
            description="New iPhone with advanced features",
            category="Electronics",
        )

        expected_keywords = ["iphone", "smartphone", "apple", "mobile", "technology"]
        self.assertEqual(result, expected_keywords)

    @patch("src.apps.ai_assistant.services.LLMChain")
    def test_generate_keywords_failure(self, mock_chain_class):
        """Test keyword generation failure fallback"""
        # Mock the chain to raise an exception
        mock_chain = MagicMock()
        mock_chain_class.return_value = mock_chain
        mock_chain.run.side_effect = Exception("API Error")

        result = self.enhancer.generate_keywords(
            title="iPhone 15",
            description="New iPhone with advanced features",
            category="Electronics",
        )

        # Should fallback to title as keyword
        self.assertEqual(result, ["iphone 15"])

    @patch("src.apps.ai_assistant.services.LLMChain")
    def test_generate_keywords_limit(self, mock_chain_class):
        """Test keyword generation respects 10 keyword limit"""
        # Mock the chain to return more than 10 keywords
        mock_chain = MagicMock()
        mock_chain_class.return_value = mock_chain
        mock_chain.run.return_value = (
            "k1, k2, k3, k4, k5, k6, k7, k8, k9, k10, k11, k12"
        )

        result = self.enhancer.generate_keywords(
            title="Test Product", description="Test description", category="Test"
        )

        # Should limit to 10 keywords
        self.assertEqual(len(result), 10)
        self.assertEqual(
            result, ["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9", "k10"]
        )
