"""Unit tests for WhatsApp utilities."""

import pytest

from src.services.whatsapp.utils import (
    extract_message_data,
    extract_user_profile,
    extract_media_info,
    normalize_phone_number,
    handle_emoji
)


class TestExtractMessageData:
    """Test cases for extract_message_data function."""
    
    def test_extract_whatsapp_business_message(self):
        """Test extracting message from WhatsApp Business API format."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg123",
                            "type": "text",
                            "from": "1234567890",
                            "to": "0987654321",
                            "timestamp": "1234567890",
                            "text": {"body": "Hello world"}
                        }]
                    }
                }]
            }]
        }
        
        result = extract_message_data(payload)
        
        assert result is not None
        assert result["message_id"] == "msg123"
        assert result["message_type"] == "text"
        assert result["from_number"] == "1234567890"
        assert result["text"] == "Hello world"
    
    def test_extract_twilio_message(self):
        """Test extracting message from Twilio format."""
        payload = {
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "Body": "Hello from Twilio",
            "MessageSid": "sid123",
            "Timestamp": "2023-01-01T00:00:00.000Z"
        }
        
        result = extract_message_data(payload)
        
        assert result is not None
        assert result["message_id"] == "sid123"
        assert result["message_type"] == "text"
        assert result["from_number"] == "whatsapp:+1234567890"
        assert result["text"] == "Hello from Twilio"
    
    def test_extract_no_message(self):
        """Test extracting when no message is present."""
        payload = {"entry": [{"changes": [{"value": {}}]}]}
        
        result = extract_message_data(payload)
        
        assert result is None
    
    def test_extract_invalid_payload(self):
        """Test extracting from invalid payload."""
        payload = {"invalid": "payload"}
        
        result = extract_message_data(payload)
        
        assert result is None


class TestExtractUserProfile:
    """Test cases for extract_user_profile function."""
    
    def test_extract_whatsapp_business_profile(self):
        """Test extracting user profile from WhatsApp Business API."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{
                            "wa_id": "1234567890",
                            "profile": {"name": "John Doe"}
                        }]
                    }
                }]
            }]
        }
        
        result = extract_user_profile(payload)
        
        assert result is not None
        assert result["wa_id"] == "1234567890"
        assert result["name"] == "John Doe"
        assert result["phone"] == "1234567890"
    
    def test_extract_twilio_profile(self):
        """Test extracting user profile from Twilio format."""
        payload = {
            "From": "whatsapp:+1234567890"
        }
        
        result = extract_user_profile(payload)
        
        assert result is not None
        assert result["wa_id"] == "+1234567890"
        assert result["name"] is None  # Twilio doesn't provide name
        assert result["phone"] == "+1234567890"
    
    def test_extract_no_profile(self):
        """Test extracting when no profile is present."""
        payload = {"entry": [{"changes": [{"value": {}}]}]}
        
        result = extract_user_profile(payload)
        
        assert result is None


class TestExtractMediaInfo:
    """Test cases for extract_media_info function."""
    
    def test_extract_whatsapp_media(self):
        """Test extracting media info from WhatsApp Business API."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg123",
                            "type": "image",
                            "image": {
                                "media_id": "media123",
                                "mime_type": "image/jpeg",
                                "sha256": "hash123",
                                "file_size": 1024
                            }
                        }]
                    }
                }]
            }]
        }
        
        result = extract_media_info(payload)
        
        assert result is not None
        assert result["media_type"] == "image"
        assert result["media_id"] == "media123"
        assert result["mime_type"] == "image/jpeg"
        assert result["sha256"] == "hash123"
        assert result["file_size"] == 1024
    
    def test_extract_text_message_no_media(self):
        """Test extracting media info from text message."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg123",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }
        
        result = extract_media_info(payload)
        
        assert result is None


class TestNormalizePhoneNumber:
    """Test cases for normalize_phone_number function."""
    
    def test_normalize_with_whatsapp_prefix(self):
        """Test normalizing number with WhatsApp prefix."""
        result = normalize_phone_number("whatsapp:+1234567890")
        assert result == "+1234567890"
    
    def test_normalize_with_plus(self):
        """Test normalizing number with plus."""
        result = normalize_phone_number("+1234567890")
        assert result == "+1234567890"
    
    def test_normalize_us_number(self):
        """Test normalizing US number without country code."""
        result = normalize_phone_number("1234567890")
        assert result == "+11234567890"
    
    def test_normalize_without_plus(self):
        """Test normalizing number without plus."""
        result = normalize_phone_number("1234567890")
        assert result == "+11234567890"
    
    def test_normalize_empty_string(self):
        """Test normalizing empty string."""
        result = normalize_phone_number("")
        assert result == ""
    
    def test_normalize_none(self):
        """Test normalizing None."""
        result = normalize_phone_number(None)
        assert result == ""


class TestHandleEmoji:
    """Test cases for handle_emoji function."""
    
    def test_handle_emoji_text(self):
        """Test handling text with emojis."""
        text = "Hello 🌍! How are you? 😊"
        result = handle_emoji(text)
        assert result == text
    
    def test_handle_emoji_empty(self):
        """Test handling empty text."""
        result = handle_emoji("")
        assert result == ""
    
    def test_handle_emoji_none(self):
        """Test handling None."""
        result = handle_emoji(None)
        assert result == ""
    
    def test_handle_emoji_unicode(self):
        """Test handling Unicode characters."""
        text = "Café 🇪🇸"
        result = handle_emoji(text)
        assert result == text
