"""Integration tests for WhatsApp sending functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.whatsapp.client import WhatsAppClient
from src.core.exceptions import WhatsAppAPIError, TwilioError


class TestWhatsAppClient:
    """Integration tests for WhatsApp client."""
    
    @pytest.fixture
    def client(self):
        """Create WhatsApp client instance."""
        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'OPENAI_API_KEY': 'test-key',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            return WhatsAppClient()
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, client):
        """Test successful message sending."""
        with patch.object(client.twilio_client.messages, 'create') as mock_create:
            mock_message = AsyncMock()
            mock_message.sid = "test-sid"
            mock_message.status = "queued"
            mock_create.return_value = mock_message
            
            result = await client.send_message("+1234567890", "Hello world")
            
            assert result["sid"] == "test-sid"
            assert result["status"] == "queued"
            assert result["body"] == "Hello world"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_failure(self, client):
        """Test message sending failure."""
        from twilio.base.exceptions import TwilioRestException
        
        with patch.object(client.twilio_client.messages, 'create') as mock_create:
            mock_create.side_effect = TwilioRestException(
                500, "Test error", "https://test.com"
            )
            
            with pytest.raises(TwilioError):
                await client.send_message("+1234567890", "Hello world")
    
    @pytest.mark.asyncio
    async def test_send_interactive_buttons(self, client):
        """Test sending interactive buttons."""
        with patch.object(client.twilio_client.messages, 'create') as mock_create:
            mock_message = AsyncMock()
            mock_message.sid = "test-sid"
            mock_message.status = "queued"
            mock_create.return_value = mock_message
            
            result = await client.send_interactive_buttons(
                "+1234567890", 
                "Choose an option:", 
                ["Option 1", "Option 2"]
            )
            
            assert result["type"] == "buttons"
            assert "Option 1" in result["body"]
            assert "Option 2" in result["body"]
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_interactive_list(self, client):
        """Test sending interactive list."""
        with patch.object(client.twilio_client.messages, 'create') as mock_create:
            mock_message = AsyncMock()
            mock_message.sid = "test-sid"
            mock_message.status = "queued"
            mock_create.return_value = mock_message
            
            rows = [
                {"id": "1", "title": "First option"},
                {"id": "2", "title": "Second option"}
            ]
            
            result = await client.send_interactive_list(
                "+1234567890",
                "Choose from list:",
                rows
            )
            
            assert result["type"] == "list"
            assert "First option" in result["body"]
            assert "Second option" in result["body"]
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_too_many_buttons_error(self, client):
        """Test error when too many buttons are provided."""
        with pytest.raises(WhatsAppAPIError, match="Maximum 3 buttons allowed"):
            await client.send_interactive_buttons(
                "+1234567890",
                "Choose:",
                ["1", "2", "3", "4"]  # 4 buttons - too many
            )
    
    @pytest.mark.asyncio
    async def test_too_many_list_items_error(self, client):
        """Test error when too many list items are provided."""
        rows = [{"id": str(i), "title": f"Option {i}"} for i in range(11)]  # 11 items
        
        with pytest.raises(WhatsAppAPIError, match="Maximum 10 list items allowed"):
            await client.send_interactive_list(
                "+1234567890",
                "Choose:",
                rows
            )
    
    @pytest.mark.asyncio
    async def test_send_media_message(self, client):
        """Test sending media message."""
        with patch.object(client.twilio_client.messages, 'create') as mock_create:
            mock_message = AsyncMock()
            mock_message.sid = "test-sid"
            mock_message.status = "queued"
            mock_create.return_value = mock_message
            
            result = await client.send_media_message(
                "+1234567890",
                "https://example.com/image.jpg",
                "Check this out!"
            )
            
            assert result["type"] == "media"
            assert result["media_url"] == "https://example.com/image.jpg"
            assert result["caption"] == "Check this out!"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_typing_state(self, client):
        """Test setting typing state."""
        # This is mostly a placeholder test since typing indicators
        # are just logged in this implementation
        result = await client.set_typing_state("+1234567890", "typing")
        
        assert result["status"] == "logged"
        assert result["to"] == "+1234567890"
        assert result["state"] == "typing"
    
    @pytest.mark.asyncio
    async def test_mark_as_read_placeholder(self, client):
        """Test mark as read (placeholder implementation)."""
        result = await client.mark_as_read("msg123")
        
        assert result["status"] == "placeholder"
        assert result["message_id"] == "msg123"
