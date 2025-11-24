"""Core orchestrator for coordinating WhatsApp message processing."""

import logging
from typing import Any, Dict, Optional

from src.core.exceptions import OrchestratorError
from src.orchestrator.flows.chat import chat_flow
from src.orchestrator.models import WhatsAppEvent
from src.orchestrator.router import MessageRouter
from src.orchestrator.session_manager import SessionManager
from src.services.llm.gateway import llm_gateway
from src.services.whatsapp.client import whatsapp_client
from src.services.whatsapp.utils import extract_message_data, extract_user_profile

logger = logging.getLogger(__name__)


class OrchestratorCore:
    """Core orchestrator for processing WhatsApp events."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        try:
            self.session_manager = SessionManager()
            self.router = MessageRouter()
            
            logger.info("Orchestrator core initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise OrchestratorError(f"Failed to initialize orchestrator: {e}")
    
    async def process_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a WhatsApp event from start to finish.
        
        Args:
            payload: Raw WhatsApp webhook payload
            
        Returns:
            Processing result
            
        Raises:
            OrchestratorError: If processing fails
        """
        try:
            # Parse the event
            event = WhatsAppEvent(payload)
            logger.info(f"Processing event from user {event.user_id}")
            
            # Mark message as read
            if event.message_id:
                await whatsapp_client.mark_as_read(event.message_id)
            
            # Set typing indicator
            await whatsapp_client.set_typing_state(event.user_id, "typing")
            
            # Get or create user session
            session = await self.session_manager.get_or_create_session(event.user_id)
            
            # Route the message to appropriate handler
            action = await self.router.route_message(event, session)
            
            # Execute the action
            result = await self._execute_action(event, session, action)
            
            # Update session
            await self.session_manager.update_session(event.user_id, session)
            
            # Stop typing indicator
            await whatsapp_client.set_typing_state(event.user_id, "stopped")
            
            logger.info(f"Event processed successfully for user {event.user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            
            # Try to send error message to user
            try:
                if 'event' in locals():
                    await whatsapp_client.send_message(
                        event.user_id,
                        "Sorry, I had trouble processing that. Can you try again? 🤔"
                    )
            except:
                pass
            
            raise OrchestratorError(f"Failed to process event: {e}")
    
    async def _execute_action(
        self, 
        event: WhatsAppEvent, 
        session: Dict[str, Any], 
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the determined action.
        
        Args:
            event: WhatsApp event
            session: User session
            action: Action to execute
            
        Returns:
            Action execution result
        """
        action_type = action.get("type")
        
        if action_type == "chat":
            return await self._handle_chat(event, session, action)
        elif action_type == "command":
            return await self._handle_command(event, session, action)
        elif action_type == "menu":
            return await self._handle_menu(event, session, action)
        elif action_type == "onboarding":
            return await self._handle_onboarding(event, session, action)
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return await self._handle_chat(event, session, action)
    
    async def _handle_chat(
        self, 
        event: WhatsAppEvent, 
        session: Dict[str, Any], 
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle chat/tutor flow via ChatFlow."""
        # This enables the "Start lesson" logic and DB exercise fetching
        return await chat_flow.run_tutor_flow(
            user_id=event.user_id,
            message=event.message_text,
            session=session
        )
    
    async def _handle_command(
        self, 
        event: WhatsAppEvent, 
        session: Dict[str, Any], 
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle command messages."""
        command = event.message_text.lower().strip()
        
        if command == "help":
            from src.services.whatsapp.templates import MessageTemplates
            response = MessageTemplates.help_menu()
            await whatsapp_client.send_message(event.user_id, response)
            return {"type": "command", "command": command, "response": response}
        
        elif command == "menu":
            from src.services.whatsapp.templates import MessageTemplates
            response = MessageTemplates.level_selection_menu()
            await whatsapp_client.send_message(event.user_id, response)
            return {"type": "command", "command": command, "response": response}
        
        elif command == "progress":
            from src.services.whatsapp.templates import MessageTemplates
            response = MessageTemplates.progress_update(
                streak=session.get("streak", 0),
                lessons_completed=session.get("lessons_completed", 0),
                current_level=session.get("level", "A1")
            )
            await whatsapp_client.send_message(event.user_id, response)
            return {"type": "command", "command": command, "response": response}
        
        else:
            # Unknown command, treat as chat
            return await self._handle_chat(event, session, action)
    
    async def _handle_menu(
        self, 
        event: WhatsAppEvent, 
        session: Dict[str, Any], 
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle menu selections."""
        # For now, just acknowledge the selection
        response = f"Thanks for selecting: {event.message_text} 🎉\n\nLet's continue with your lesson!"
        await whatsapp_client.send_message(event.user_id, response)
        return {"type": "menu", "selection": event.message_text, "response": response}
    
    async def _handle_onboarding(
        self, 
        event: WhatsAppEvent, 
        session: Dict[str, Any], 
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle onboarding flow via ChatFlow."""
        return await chat_flow.run_onboarding_flow(
            user_id=event.user_id,
            message=event.message_text,
            session=session
        )
    
    def _get_tutor_prompt(self, context: Dict[str, Any]) -> str:
        """Get the tutor system prompt with context."""
        from src.services.llm.prompts.manager import prompt_manager
        
        try:
            return prompt_manager.render_prompt("tutor.jinja2", context)
        except Exception as e:
            logger.error(f"Error rendering tutor prompt: {e}")
            # Fallback prompt
            return "You are a friendly AI language tutor. Be encouraging and helpful."


# Global orchestrator instance
orchestrator = OrchestratorCore()
