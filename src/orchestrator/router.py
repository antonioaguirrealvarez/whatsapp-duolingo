"""Message router for directing messages to appropriate handlers."""

import logging
from typing import Any, Dict

from src.core.exceptions import OrchestratorError
from src.orchestrator.models import WhatsAppEvent

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes incoming messages to appropriate handlers based on content and context."""
    
    def __init__(self):
        """Initialize the message router."""
        logger.info("Message router initialized")
    
    async def route_message(
        self, 
        event: WhatsAppEvent, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route a message to the appropriate handler.
        
        Args:
            event: WhatsApp event containing the message
            session: User session data
            
        Returns:
            Action dictionary with handler information
        """
        try:
            # Check if user is new (onboarding)
            if session.get("is_new_user", True):
                return {
                    "type": "onboarding",
                    "handler": "onboarding",
                    "context": "New user onboarding"
                }
            
            # Handle commands first
            if event.is_command:
                return {
                    "type": "command",
                    "handler": "command",
                    "command": event.message_text.lower().strip()
                }
            
            # Handle greetings
            if event.is_greeting:
                return {
                    "type": "chat",
                    "handler": "chat",
                    "context": "Greeting response"
                }
            
            # Check for menu selections (numbers)
            if self._is_menu_selection(event.message_text):
                return {
                    "type": "menu",
                    "handler": "menu",
                    "selection": event.message_text
                }
            
            # Check for lesson responses
            if session.get("in_lesson", False):
                return {
                    "type": "lesson_response",
                    "handler": "lesson",
                    "context": "Lesson answer evaluation"
                }
            
            # Default to chat
            return {
                "type": "chat",
                "handler": "chat",
                "context": "General conversation"
            }
            
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            # Default to chat on error
            return {
                "type": "chat",
                "handler": "chat",
                "context": "Error fallback"
            }
    
    def _is_menu_selection(self, text: str) -> bool:
        """
        Check if the text is a menu selection.
        
        Args:
            text: Message text to check
            
        Returns:
            True if this looks like a menu selection
        """
        if not text:
            return False
        
        # Check for single digit (1-9)
        if text.strip().isdigit() and len(text.strip()) == 1:
            return True
        
        # Check for letter (A-Z)
        if len(text.strip()) == 1 and text.strip().isalpha():
            return True
        
        # Check for common selection patterns
        selection_patterns = [
            "option", "choose", "select", "answer"
        ]
        
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in selection_patterns)
    
    def classify_intent(self, text: str) -> str:
        """
        Classify the intent of a message.
        
        Args:
            text: Message text to classify
            
        Returns:
            Intent classification
        """
        text_lower = text.lower().strip()
        
        # Learning intents
        learning_keywords = [
            "learn", "study", "practice", "lesson", "exercise",
            "question", "help me", "how do", "what is", "explain"
        ]
        
        if any(keyword in text_lower for keyword in learning_keywords):
            return "learning"
        
        # Greeting intents
        greeting_keywords = [
            "hi", "hello", "hola", "hey", "good morning", "good evening"
        ]
        
        if any(keyword in text_lower for keyword in greeting_keywords):
            return "greeting"
        
        # Progress intents
        progress_keywords = [
            "progress", "score", "level", "streak", "how am i doing"
        ]
        
        if any(keyword in text_lower for keyword in progress_keywords):
            return "progress"
        
        # Help intents
        help_keywords = [
            "help", "menu", "options", "what can i do", "commands"
        ]
        
        if any(keyword in text_lower for keyword in help_keywords):
            return "help"
        
        # Default to conversation
        return "conversation"
