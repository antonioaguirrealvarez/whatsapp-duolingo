"""Unit tests for configuration module."""

import pytest
from unittest.mock import patch

from src.core.config import Settings, get_settings


class TestSettings:
    """Test cases for Settings class."""
    
    def test_settings_initialization(self):
        """Test that Settings can be initialized."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            settings = Settings()
            
            assert settings.OPENAI_API_KEY == 'test-key'
            assert settings.TWILIO_ACCOUNT_SID == 'test-sid'
            assert settings.TWILIO_AUTH_TOKEN == 'test-token'
            assert settings.FIRECRAWL_API_KEY == 'test-firecrawl-key'
    
    def test_twilio_client_params(self):
        """Test Twilio client parameters extraction."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            settings = Settings()
            params = settings.twilio_client_params
            
            assert params['account_sid'] == 'test-sid'
            assert params['auth_token'] == 'test-token'
    
    def test_openai_client_params(self):
        """Test OpenAI client parameters extraction."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'OPENAI_MODEL': 'gpt-4',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            settings = Settings()
            params = settings.openai_client_params
            
            assert params['api_key'] == 'test-key'
            assert params['model'] == 'gpt-4'
    
    def test_langsmith_config_enabled(self):
        """Test LangSmith configuration when enabled."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key',
            'LANGSMITH_TRACING': 'true',
            'LANGSMITH_API_KEY': 'test-langsmith-key'
        }):
            settings = Settings()
            config = settings.langsmith_config
            
            assert config['tracing'] is True
            assert config['api_key'] == 'test-langsmith-key'
    
    def test_langsmith_config_disabled(self):
        """Test LangSmith configuration when disabled."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key',
            'LANGSMITH_TRACING': 'false'
        }):
            settings = Settings()
            config = settings.langsmith_config
            
            assert config == {}


class TestGetSettings:
    """Test cases for get_settings function."""
    
    def test_get_settings_returns_instance(self):
        """Test that get_settings returns Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
        # Just check it's an instance, not the specific values
        # since global instance uses real env vars
