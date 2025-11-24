"""Data models for orchestrator components."""

from typing import Any, Dict, Optional

from src.services.whatsapp.utils import extract_message_data, extract_user_profile


class WhatsAppEvent:
    """Represents a WhatsApp event/message."""
    
    def __init__(self, payload: Dict[str, Any]):
        """Initialize the WhatsApp event."""
        self.payload = payload
        self.message_data = extract_message_data(payload)
        self.user_profile = extract_user_profile(payload)
        
        if not self.message_data:
            from src.core.exceptions import OrchestratorError
            raise OrchestratorError("No message data found in payload")
        
        self.user_id = self.message_data.get("from_number")
        self.message_type = self.message_data.get("message_type", "text")
        self.message_text = self.message_data.get("text", "")
        self.message_id = self.message_data.get("message_id")
        
    @property
    def is_command(self) -> bool:
        """Check if this is a command message."""
        if not self.message_text:
            return False
        
        commands = ["menu", "help", "progress", "streak", "stop", "start"]
        return self.message_text.lower().strip() in commands
    
    @property
    def is_greeting(self) -> bool:
        """Check if this is a greeting message."""
        if not self.message_text:
            return False
        
        greetings = ["hola", "hello", "hi", "hey", "buenos días", "buenas"]
        return any(greeting in self.message_text.lower() for greeting in greetings)
