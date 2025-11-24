"""End-to-end tests for the complete WhatsApp flow."""

import pytest
from unittest.mock import AsyncMock, patch

from src.orchestrator.core import OrchestratorCore
from src.orchestrator.models import WhatsAppEvent
from src.services.whatsapp.client import whatsapp_client


class TestFullFlow:
    """End-to-end tests for the complete message processing flow."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return OrchestratorCore()
    
    @pytest.fixture
    def sample_whatsapp_payload(self):
        """Sample WhatsApp webhook payload."""
        return {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{
                            "wa_id": "1234567890",
                            "profile": {"name": "John Doe"}
                        }],
                        "messages": [{
                            "id": "msg123",
                            "type": "text",
                            "from": "1234567890",
                            "to": "0987654321",
                            "timestamp": "1234567890",
                            "text": {"body": "Hola"}
                        }]
                    }
                }]
            }]
        }
    
    @pytest.mark.asyncio
    async def test_new_user_greeting_flow(self, orchestrator, sample_whatsapp_payload):
        """Test complete flow for new user greeting - now goes through onboarding."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            with patch.object(whatsapp_client, 'send_message') as mock_send, \
                 patch.object(whatsapp_client, 'mark_as_read') as mock_read, \
                 patch.object(whatsapp_client, 'set_typing_state') as mock_typing:
                
                mock_send.return_value = {"sid": "test-sid"}
                
                # Process the message (new user goes through onboarding)
                result = await orchestrator.process_event(sample_whatsapp_payload)
                
                # Verify onboarding flow was triggered
                assert result["type"] == "onboarding_complete"
                assert result["native_language"] == "Portuguese"
                assert result["target_language"] == "English"
                assert result["level"] == "B1"
                
                # Verify WhatsApp operations were called
                mock_read.assert_called_once_with("msg123")
                mock_typing.assert_any_call("1234567890", "typing")
                mock_typing.assert_any_call("1234567890", "stopped")
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_command_flow(self, orchestrator, sample_whatsapp_payload):
        """Test command handling flow - now goes through onboarding first."""
        # Modify payload to contain a command
        sample_whatsapp_payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "help"
        
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            with patch.object(whatsapp_client, 'send_message') as mock_send, \
                 patch.object(whatsapp_client, 'mark_as_read') as mock_read, \
                 patch.object(whatsapp_client, 'set_typing_state') as mock_typing:
                
                # Process the command (new user goes through onboarding first)
                result = await orchestrator.process_event(sample_whatsapp_payload)
                
                # Verify onboarding was completed first
                assert result["type"] == "onboarding_complete"
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lesson_flow(self, orchestrator, sample_whatsapp_payload):
        """Test lesson flow - onboarding first, then lesson."""
        # Modify payload to request a lesson
        sample_whatsapp_payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "I want to practice"
        
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            with patch.object(whatsapp_client, 'send_message') as mock_send, \
                 patch.object(whatsapp_client, 'mark_as_read') as mock_read, \
                 patch.object(whatsapp_client, 'set_typing_state') as mock_typing, \
                 patch('src.services.llm.gateway.llm_gateway.generate_exercise') as mock_exercise, \
                 patch('src.orchestrator.flows.chat.ExerciseRepository') as mock_repo:
                
                # Setup mock exercise
                mock_exercise.return_value = {
                    "question": "What is 'hello' in English?",
                    "correct_answer": "Hello",
                    "options": ["Hello", "Goodbye", "Thanks", "Please"],
                    "explanation": "'Hello' is the standard greeting"
                }
                
                # Mock repository to return None (force LLM fallback)
                mock_repo_instance = mock_repo.return_value
                mock_repo_instance.get_random_exercise.return_value = None
                
                # Process the lesson request (new user goes through onboarding first)
                result = await orchestrator.process_event(sample_whatsapp_payload)
                
                # Verify onboarding was completed first
                assert result["type"] == "onboarding_complete"
                
                # Now send another message for lesson (user is no longer new)
                sample_whatsapp_payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "start lesson"
                result = await orchestrator.process_event(sample_whatsapp_payload)
                
                # Verify lesson was generated
                assert result["type"] == "lesson_start"
                assert "exercise" in result
                mock_exercise.assert_called_once()
                assert mock_send.call_count >= 2  # Once for onboarding, once for lesson
    
    @pytest.mark.asyncio
    async def test_session_persistence(self, orchestrator, sample_whatsapp_payload):
        """Test that session data persists across messages."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            with patch.object(whatsapp_client, 'send_message') as mock_send, \
                 patch.object(whatsapp_client, 'mark_as_read') as mock_read, \
                 patch.object(whatsapp_client, 'set_typing_state') as mock_typing:
                
                mock_send.return_value = {"sid": "test-sid"}
                
                # Send first message (onboarding)
                await orchestrator.process_event(sample_whatsapp_payload)
                
                # Check session was created and user is no longer new
                session = await orchestrator.session_manager.get_or_create_session("1234567890")
                assert session["user_id"] == "1234567890"
                assert session["is_new_user"] is False
                
                # Send second message (should go to tutor flow now)
                await orchestrator.process_event(sample_whatsapp_payload)
                
                # Check session persists
                session = await orchestrator.session_manager.get_or_create_session("1234567890")
                assert len(session["history"]) > 0  # Should have conversation history
    
    @pytest.mark.asyncio
    async def test_error_handling(self, orchestrator, sample_whatsapp_payload):
        """Test error handling in the flow."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            with patch.object(whatsapp_client, 'send_message') as mock_send, \
                 patch.object(whatsapp_client, 'mark_as_read') as mock_read, \
                 patch.object(whatsapp_client, 'set_typing_state') as mock_typing:
                
                # Make WhatsApp client fail
                mock_send.side_effect = Exception("WhatsApp error")
                
                # Process should handle error gracefully
                with pytest.raises(Exception):  # Should raise OrchestratorError
                    await orchestrator.process_event(sample_whatsapp_payload)
                
                # Should still attempt to send error message
                assert mock_send.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_twilio_payload_format(self, orchestrator):
        """Test handling Twilio payload format - goes through onboarding first."""
        twilio_payload = {
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "Body": "Hello from Twilio",
            "MessageSid": "sid123",
            "Timestamp": "2023-01-01T00:00:00.000Z"
        }
        
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
            'YOUR_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
            'FIRECRAWL_API_KEY': 'test-firecrawl-key'
        }):
            with patch.object(whatsapp_client, 'send_message') as mock_send, \
                 patch.object(whatsapp_client, 'mark_as_read') as mock_read, \
                 patch.object(whatsapp_client, 'set_typing_state') as mock_typing:
                
                mock_send.return_value = {"sid": "test-sid"}
                
                # Process Twilio message (new user goes through onboarding)
                result = await orchestrator.process_event(twilio_payload)
                
                # Verify it was processed as onboarding
                assert result["type"] == "onboarding_complete"
                mock_send.assert_called_once()
