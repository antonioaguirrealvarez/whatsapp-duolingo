"""Unit tests for LangSmith integration."""

import pytest
from unittest.mock import MagicMock, patch
from src.services.llm.langsmith_client import LangSmithManager


class TestLangSmithManager:
    """Test suite for LangSmithManager."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        with patch('src.services.llm.langsmith_client.get_settings') as mock_get:
            settings = MagicMock()
            settings.LANGSMITH_TRACING = True
            settings.LANGSMITH_API_KEY = "test-api-key"
            settings.LANGSMITH_PROJECT = "test-project"
            settings.LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"
            mock_get.return_value = settings
            yield settings
            
    @pytest.fixture
    def manager(self, mock_settings):
        """Create manager with mocked dependencies."""
        with patch('src.services.llm.langsmith_client.LangSmithClient'):
            return LangSmithManager()

    def test_initialization_enabled(self, manager, mock_settings):
        """Test initialization when tracing is enabled."""
        assert manager.is_enabled()
        assert manager.client is not None

    def test_initialization_disabled(self, mock_settings):
        """Test initialization when tracing is disabled."""
        mock_settings.LANGSMITH_TRACING = False
        manager = LangSmithManager()
        assert not manager.is_enabled()
        assert manager.client is None

    def test_log_interaction(self, manager):
        """Test logging user interaction."""
        manager.log_user_interaction(
            user_id="123",
            message="Hello",
            response="Hi there",
            metadata={"latency": 100}
        )
        # Verify no exceptions are raised
        assert True

    def test_trace_llm_call(self, manager):
        """Test tracing LLM call."""
        manager.trace_llm_call(
            model_name="gpt-4",
            prompt="test prompt",
            response="test response",
            tokens_used=10,
            latency_ms=500
        )
        # Verify no exceptions are raised
        assert True
