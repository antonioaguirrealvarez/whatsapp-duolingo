"""WhatsApp client for sending messages via Twilio API."""

import logging
from typing import Any, Dict, List, Optional

import httpx
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

from src.core.config import get_settings
from src.core.exceptions import TwilioError, WhatsAppAPIError
from src.services.whatsapp.utils import normalize_phone_number

logger = logging.getLogger(__name__)
settings = get_settings()


class WhatsAppClient:
    """WhatsApp client using Twilio API for outbound messaging."""
    
    def __init__(self):
        """Initialize the WhatsApp client."""
        try:
            self.twilio_client = TwilioClient(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.from_number = settings.TWILIO_WHATSAPP_NUMBER
            logger.info("WhatsApp client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp client: {e}")
            raise TwilioError(f"Failed to initialize client: {e}")
    
    async def send_message(self, to: str, body: str) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp.
        
        Args:
            to: Recipient phone number
            body: Message content
            
        Returns:
            Message information from Twilio
            
        Raises:
            WhatsAppAPIError: If message sending fails
        """
        try:
            to_normalized = normalize_phone_number(to)
            
            logger.info(f"Sending WhatsApp message to {to_normalized}")
            
            message = self.twilio_client.messages.create(
                body=body,
                from_=self.from_number,
                to=f"whatsapp:{to_normalized}"
            )
            
            logger.info(f"Message sent successfully: {message.sid}")
            
            return {
                "sid": message.sid,
                "status": message.status,
                "to": to_normalized,
                "from": self.from_number,
                "body": body,
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error: {e}")
            raise TwilioError(f"Failed to send message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            raise WhatsAppAPIError(f"Failed to send message: {e}")
    
    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.
        
        Note: This is more complex with Twilio and typically requires
        WhatsApp Business API. For now, this is a placeholder.
        
        Args:
            message_id: ID of the message to mark as read
            
        Returns:
            Operation result
        """
        # TODO: Implement message read functionality
        # This typically requires WhatsApp Business API
        logger.info(f"Marking message {message_id} as read (placeholder)")
        return {"status": "placeholder", "message_id": message_id}
    
    async def set_typing_state(self, to: str, state: str = "typing") -> Dict[str, Any]:
        """
        Set typing indicator for a user.
        
        Args:
            to: Recipient phone number
            state: Typing state ('typing' or 'stopped')
            
        Returns:
            Operation result
        """
        try:
            to_normalized = normalize_phone_number(to)
            
            # For Twilio, we can send a typing indicator message
            if state == "typing":
                # Send empty message with typing indicator
                # Note: This is a simplified approach
                logger.info(f"Setting typing state to '{state}' for {to_normalized}")
                
                # In a real implementation, this would use WhatsApp Business API
                # For now, we'll just log it
                return {
                    "status": "logged",
                    "to": to_normalized,
                    "state": state,
                }
            else:
                logger.info(f"Setting typing state to '{state}' for {to_normalized}")
                return {
                    "status": "logged",
                    "to": to_normalized,
                    "state": state,
                }
                
        except Exception as e:
            logger.error(f"Error setting typing state: {e}")
            raise WhatsAppAPIError(f"Failed to set typing state: {e}")
    
    async def send_interactive_buttons(
        self, 
        to: str, 
        text: str, 
        buttons: List[str]
    ) -> Dict[str, Any]:
        """
        Send interactive buttons message.
        
        Args:
            to: Recipient phone number
            text: Message text
            buttons: List of button texts (max 3)
            
        Returns:
            Message information
        """
        try:
            to_normalized = normalize_phone_number(to)
            
            if len(buttons) > 3:
                raise ValueError("Maximum 3 buttons allowed")
            
            # For Twilio, we can use the template system or send numbered options
            # For now, we'll format as a numbered list
            button_text = "\n".join([f"{i+1}. {button}" for i, button in enumerate(buttons)])
            full_text = f"{text}\n\n{button_text}\n\nReply with the number of your choice:"
            
            logger.info(f"Sending buttons message to {to_normalized}")
            
            message = self.twilio_client.messages.create(
                body=full_text,
                from_=self.from_number,
                to=f"whatsapp:{to_normalized}"
            )
            
            logger.info(f"Buttons message sent: {message.sid}")
            
            return {
                "sid": message.sid,
                "status": message.status,
                "to": to_normalized,
                "from": self.from_number,
                "body": full_text,
                "type": "buttons",
                "buttons": buttons,
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error sending buttons: {e}")
            raise TwilioError(f"Failed to send buttons: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending buttons: {e}")
            raise WhatsAppAPIError(f"Failed to send buttons: {e}")
    
    async def send_interactive_list(
        self, 
        to: str, 
        header: str, 
        rows: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Send interactive list message.
        
        Args:
            to: Recipient phone number
            header: List header text
            rows: List of row dictionaries with 'id' and 'title' keys
            
        Returns:
            Message information
        """
        try:
            to_normalized = normalize_phone_number(to)
            
            if len(rows) > 10:
                raise ValueError("Maximum 10 list items allowed")
            
            # For Twilio, format as numbered list
            list_text = "\n".join([f"{i+1}. {row['title']}" for i, row in enumerate(rows)])
            full_text = f"{header}\n\n{list_text}\n\nReply with the number of your choice:"
            
            logger.info(f"Sending list message to {to_normalized}")
            
            message = self.twilio_client.messages.create(
                body=full_text,
                from_=self.from_number,
                to=f"whatsapp:{to_normalized}"
            )
            
            logger.info(f"List message sent: {message.sid}")
            
            return {
                "sid": message.sid,
                "status": message.status,
                "to": to_normalized,
                "from": self.from_number,
                "body": full_text,
                "type": "list",
                "header": header,
                "rows": rows,
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error sending list: {e}")
            raise TwilioError(f"Failed to send list: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending list: {e}")
            raise WhatsAppAPIError(f"Failed to send list: {e}")
    
    async def send_media_message(
        self, 
        to: str, 
        media_url: str, 
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a media message (image, audio, etc.).
        
        Args:
            to: Recipient phone number
            media_url: URL of the media file
            caption: Optional caption for the media
            
        Returns:
            Message information
        """
        try:
            to_normalized = normalize_phone_number(to)
            
            logger.info(f"Sending media message to {to_normalized}")
            
            message = self.twilio_client.messages.create(
                media_url=[media_url],
                from_=self.from_number,
                to=f"whatsapp:{to_normalized}",
                body=caption or ""
            )
            
            logger.info(f"Media message sent: {message.sid}")
            
            return {
                "sid": message.sid,
                "status": message.status,
                "to": to_normalized,
                "from": self.from_number,
                "media_url": media_url,
                "caption": caption,
                "type": "media",
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error sending media: {e}")
            raise TwilioError(f"Failed to send media: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending media: {e}")
            raise WhatsAppAPIError(f"Failed to send media: {e}")


# Global client instance
whatsapp_client = WhatsAppClient()
