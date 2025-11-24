"""WhatsApp message parsing and utility functions."""

import logging
from typing import Any, Dict, Optional

from src.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def extract_message_data(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract message data from WhatsApp webhook payload.
    
    Args:
        payload: Raw webhook payload from WhatsApp/Twilio
        
    Returns:
        Dictionary containing message data or None if no message found
        
    Raises:
        ValidationError: If payload structure is invalid
    """
    try:
        # Handle different payload structures (WhatsApp vs Twilio)
        
        # WhatsApp Business API format
        if "entry" in payload:
            entries = payload.get("entry", [])
            if not entries:
                return None
                
            entry = entries[0]
            changes = entry.get("changes", [])
            if not changes:
                return None
                
            change = changes[0]
            messages_data = change.get("value", {}).get("messages", [])
            if not messages_data:
                return None
                
            message = messages_data[0]
            
            return {
                "message_id": message.get("id"),
                "message_type": message.get("type", "text"),
                "from_number": message.get("from"),
                "to_number": message.get("to"),
                "timestamp": message.get("timestamp"),
                "text": message.get("text", {}).get("body") if message.get("type") == "text" else None,
                "media_id": message.get(message.get("type"), {}).get("media_id") if message.get("type") != "text" else None,
                "interactive": message.get("interactive"),
                "context": message.get("context"),
                "raw": message,
            }
        
        # Twilio format
        elif "From" in payload and "To" in payload:
            return {
                "message_id": payload.get("MessageSid"),
                "message_type": "text",  # Twilio sends text by default
                "from_number": payload.get("From"),
                "to_number": payload.get("To"),
                "timestamp": payload.get("Timestamp"),
                "text": payload.get("Body"),
                "media_id": payload.get("MediaUrl0"),
                "interactive": None,
                "context": None,
                "raw": payload,
            }
        
        else:
            logger.warning(f"Unknown payload format: {payload}")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting message data: {e}")
        raise ValidationError(f"Invalid message payload: {e}")


def extract_user_profile(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract user profile information from WhatsApp webhook payload.
    
    Args:
        payload: Raw webhook payload from WhatsApp/Twilio
        
    Returns:
        Dictionary containing user profile data or None if not found
    """
    try:
        # WhatsApp Business API format
        if "entry" in payload:
            entries = payload.get("entry", [])
            if not entries:
                return None
                
            entry = entries[0]
            changes = entry.get("changes", [])
            if not changes:
                return None
                
            change = changes[0]
            contacts = change.get("value", {}).get("contacts", [])
            if not contacts:
                return None
                
            contact = contacts[0]
            
            return {
                "wa_id": contact.get("wa_id"),
                "name": contact.get("profile", {}).get("name"),
                "phone": contact.get("wa_id"),
            }
        
        # Twilio format - limited profile information
        elif "From" in payload:
            from_number = payload.get("From", "").replace("whatsapp:", "")
            return {
                "wa_id": from_number,
                "name": None,  # Twilio doesn't provide profile name
                "phone": from_number,
            }
        
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error extracting user profile: {e}")
        return None


def extract_media_info(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract media information from WhatsApp webhook payload.
    
    Args:
        payload: Raw webhook payload from WhatsApp/Twilio
        
    Returns:
        Dictionary containing media information or None if no media found
    """
    try:
        message_data = extract_message_data(payload)
        if not message_data:
            return None
        
        message_type = message_data.get("message_type")
        if message_type == "text":
            return None
        
        # WhatsApp Business API format
        if "entry" in payload:
            entries = payload.get("entry", [])
            entry = entries[0]
            changes = entry.get("changes", [])
            change = changes[0]
            messages_data = change.get("value", {}).get("messages", [])
            message = messages_data[0]
            
            media_data = message.get(message_type, {})
            
            return {
                "media_type": message_type,
                "media_id": media_data.get("media_id"),
                "mime_type": media_data.get("mime_type"),
                "sha256": media_data.get("sha256"),
                "file_size": media_data.get("file_size"),
            }
        
        # Twilio format
        elif "MediaUrl0" in payload:
            return {
                "media_type": payload.get("MediaContentType0", "unknown"),
                "media_id": payload.get("MediaUrl0"),
                "mime_type": payload.get("MediaContentType0"),
                "sha256": None,
                "file_size": None,
            }
        
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error extracting media info: {e}")
        return None


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to consistent format.
    
    Args:
        phone: Phone number in various formats
        
    Returns:
        Normalized phone number
    """
    if not phone:
        return ""
    
    # Remove WhatsApp prefix if present
    phone = phone.replace("whatsapp:", "")
    
    # Remove any non-digit characters except +
    phone = "".join(c for c in phone if c.isdigit() or c == "+")
    
    # Ensure it starts with +
    if not phone.startswith("+"):
        # Assume it's a US number if no country code
        if len(phone) == 10:
            phone = f"+1{phone}"
        else:
            phone = f"+{phone}"
    
    return phone


def handle_emoji(text: str) -> str:
    """
    Ensure emoji encoding works properly.
    
    Args:
        text: Text that may contain emojis
        
    Returns:
        Text with properly encoded emojis
    """
    if not text:
        return ""
    
    # Ensure proper Unicode handling
    # This is mainly a placeholder for future emoji processing
    return text.encode('utf-8', errors='ignore').decode('utf-8')
