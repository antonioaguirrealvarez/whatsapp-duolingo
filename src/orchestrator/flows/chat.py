"""Chat flow coordination logic for handling conversation flows."""

import logging
from typing import Any, Dict, Optional

from src.core.exceptions import OrchestratorError
from src.data.repositories.exercise_repo import ExerciseRepository
from src.services.llm.evals.judge_correctness import get_evaluator
from src.services.llm.gateway import llm_gateway
from src.services.whatsapp.client import whatsapp_client
from src.services.whatsapp.templates import MessageTemplates

logger = logging.getLogger(__name__)


class ChatFlow:
    """Coordinates chat-based conversation flows."""
    
    def __init__(self):
        """Initialize the chat flow coordinator."""
        logger.info("Chat flow coordinator initialized")
    
    async def run_chat_flow(
        self, 
        user_id: str, 
        message: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run the main chat flow.
        
        Args:
            user_id: User's WhatsApp ID
            message: User's message
            session: User session data
            
        Returns:
            Flow execution result
        """
        try:
            # Get conversation history
            history = session.get("history", [])
            
            # Prepare context for LLM
            context = self._prepare_context(session)
            
            # Get LLM response
            response = await llm_gateway.get_response(
                user_text=message,
                conversation_history=history,
                system_prompt=self._get_system_prompt(context)
            )
            
            # Send response to user
            await whatsapp_client.send_message(user_id, response)
            
            # Update session
            await self._update_session_after_chat(session, message, response)
            
            return {
                "type": "chat",
                "user_message": message,
                "bot_response": response,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"Error in chat flow: {e}")
            raise OrchestratorError(f"Failed to run chat flow: {e}")
    
    async def run_tutor_flow(
        self, 
        user_id: str, 
        message: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run the tutor flow for language learning.
        
        Args:
            user_id: User's WhatsApp ID
            message: User's message
            session: User session data
            
        Returns:
            Flow execution result
        """
        try:
            # Check if user wants to start a lesson
            if self._should_start_lesson(message, session):
                return await self._start_lesson(user_id, session)
            
            # Check if user is answering a question
            if session.get("in_lesson", False):
                return await self._handle_lesson_answer(user_id, message, session)
            
            # Default to regular chat
            return await self.run_chat_flow(user_id, message, session)
            
        except Exception as e:
            logger.error(f"Error in tutor flow: {e}")
            raise OrchestratorError(f"Failed to run tutor flow: {e}")
    
    async def run_onboarding_flow(
        self, 
        user_id: str, 
        message: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simplified onboarding flow for MVP - defaults to Spanish->English B1.
        
        Args:
            user_id: User's WhatsApp ID
            message: User's message
            session: User session data
            
        Returns:
            Flow execution result
        """
        try:
            # Check if user is new and complete onboarding immediately
            if session.get("is_new_user", False):
                # Set default values for MVP
                session["native_language"] = "Portuguese"
                session["target_language"] = "English"
                session["level"] = "B1"
                session["learning_goal"] = "General fluency"
                session["state"] = "chat"
                session["is_new_user"] = False
                
                # Send welcome message with default setup
                welcome_msg = (
                    "Olá! Welcome to your language learning assistant! 🎓\n\n"
                    "We've set you up with:\n"
                    "📚 Level: B1 English\n"
                    "🌍 From: Portuguese\n"
                    "🎯 Goal: General fluency\n\n"
                    "Ready to start? Send 'start lesson' to begin practicing! 🚀"
                )
                
                await whatsapp_client.send_message(user_id, welcome_msg)
                
                logger.info(f"Completed simplified onboarding for user {user_id}")
                
                return {
                    "type": "onboarding_complete",
                    "native_language": "Portuguese",
                    "target_language": "English", 
                    "level": "B1",
                    "learning_goal": "General fluency"
                }
            else:
                # User is not new, proceed with regular chat
                return await self.run_chat_flow(user_id, message, session)
                
        except Exception as e:
            logger.error(f"Error in onboarding flow: {e}")
            raise OrchestratorError(f"Failed to run onboarding flow: {e}")
    
    def _prepare_context(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for LLM prompt."""
        return {
            "user_name": session.get("user_name"),
            "current_level": session.get("level", "A1"),
            "native_language": session.get("native_language", "Spanish"),
            "target_language": session.get("target_language", "English"),
            "learning_goal": session.get("learning_goal", "General fluency"),
            "user_country": session.get("country", "Mexico"),
            "streak": session.get("streak", 0),
            "lessons_completed": session.get("lessons_completed", 0),
            "context": "Language learning conversation"
        }
    
    def _get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Get system prompt with context."""
        from src.services.llm.prompts.manager import prompt_manager
        
        try:
            return prompt_manager.render_prompt("tutor.jinja2", context)
        except Exception as e:
            logger.error(f"Error rendering system prompt: {e}")
            # Fallback prompt
            return "You are a friendly AI language tutor. Be encouraging and helpful."
    
    async def _update_session_after_chat(
        self, 
        session: Dict[str, Any], 
        user_message: str, 
        bot_response: str
    ) -> None:
        """Update session after chat interaction."""
        history = session.get("history", [])
        
        # Add messages to history
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": bot_response})
        
        # Keep only last 10 messages
        session["history"] = history[-10:]
        session["last_activity"] = "chat"
    
    def _should_start_lesson(self, message: str, session: Dict[str, Any]) -> bool:
        """Check if user wants to start a lesson."""
        lesson_keywords = [
            "lesson", "practice", "exercise", "learn", "study",
            "start", "begin", "quiero aprender", "quiero practicar"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in lesson_keywords)
    
    async def _start_lesson(self, user_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Start a language lesson using pre-generated content from database."""
        try:
            # Initialize ExerciseRepository
            repo = ExerciseRepository()
            
            # Get user preferences (default to Portuguese->English B1 for MVP)
            source_lang = session.get("native_language", "Portuguese").lower()[:2]  # pt
            # Ensure Portuguese maps to "pt" not "po"
            if source_lang == "po":
                source_lang = "pt"
            target_lang = session.get("target_language", "English").lower()[:2]   # en
            difficulty_level = session.get("level", "B1")
            
            # Fetch a random exercise from database
            exercise = repo.get_random_exercise(
                source_lang=source_lang,
                target_lang=target_lang,
                difficulty_level=difficulty_level
            )
            
            if not exercise:
                # Fallback to LLM generation if no exercises in DB
                logger.warning(f"No exercises found in DB for {source_lang}->{target_lang} {difficulty_level}, falling back to LLM")
                exercise_data = await llm_gateway.generate_exercise(
                    topic="Daily conversation",
                    difficulty=difficulty_level,
                    exercise_type="multiple_choice",
                    target_language=target_lang,
                    native_language=source_lang
                )
                
                question_text = MessageTemplates.format_multiple_choice(
                    exercise_data["question"],
                    exercise_data["options"]
                )
                
                # Store in session
                session["in_lesson"] = True
                session["current_lesson"] = exercise_data
                session["current_exercise_id"] = None  # No DB ID
                session["current_expected_output"] = exercise_data.get("correct_answer")
                
                await whatsapp_client.send_message(user_id, question_text)
                
                return {
                    "type": "lesson_start",
                    "exercise": exercise_data,
                    "question": question_text,
                    "source": "llm_fallback"
                }
            
            # Format the question using DB exercise content
            question_text = f"{exercise.exercise_introduction}\n\n{exercise.exercise_input}"
            
            # Send question to user
            await whatsapp_client.send_message(user_id, question_text)
            
            # Update session with DB exercise info
            session["in_lesson"] = True
            session["current_lesson"] = {
                "id": exercise.id,
                "question": question_text,
                "exercise_type": exercise.exercise_type,
                "topic": exercise.topic_id
            }
            session["current_exercise_id"] = exercise.id
            session["current_expected_output"] = exercise.expected_output
            
            logger.info(f"Started lesson with DB exercise {exercise.id} for user {user_id}")
            
            return {
                "type": "lesson_start",
                "exercise": exercise,
                "question": question_text,
                "source": "database"
            }
            
        except Exception as e:
            logger.error(f"Error starting lesson: {e}")
            raise OrchestratorError(f"Failed to start lesson: {e}")
    
    async def _handle_lesson_answer(
        self, 
        user_id: str, 
        message: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle answer to lesson question using LLM evaluator."""
        try:
            # Get current lesson info from session
            current_lesson = session.get("current_lesson")
            expected_output = session.get("current_expected_output")
            
            if not current_lesson or not expected_output:
                # No active lesson, reset state
                session["in_lesson"] = False
                session["current_exercise_id"] = None
                session["current_expected_output"] = None
                return await self.run_chat_flow(user_id, message, session)
            
            # Use LLM evaluator to assess the answer
            evaluator = get_evaluator()
            evaluation = await evaluator.evaluate_response(
                question=current_lesson.get("question", "Language exercise"),
                user_answer=message,
                rubric=f"Expected answer: {expected_output}"
            )
            
            # Send feedback based on evaluation
            if evaluation.get("is_correct", False):
                feedback = MessageTemplates.correct_answer_feedback(
                    message,
                    evaluation.get("explanation", "Correct! Well done!")
                )
            else:
                feedback = MessageTemplates.incorrect_answer_feedback(
                    message,
                    expected_output,
                    evaluation.get("explanation", "Try again!")
                )
            
            await whatsapp_client.send_message(user_id, feedback)
            
            # Update session to clear lesson state
            session["in_lesson"] = False
            session["current_lesson"] = None
            session["current_exercise_id"] = None
            session["current_expected_output"] = None
            
            # Increment lesson count if correct
            if evaluation.get("is_correct", False):
                from src.orchestrator.session_manager import SessionManager
                session_manager = SessionManager()
                await session_manager.increment_lessons_completed(user_id)
            
            logger.info(f"Evaluated answer for user {user_id}: correct={evaluation.get('is_correct')}")
            
            return {
                "type": "lesson_answer",
                "evaluation": evaluation,
                "feedback": feedback
            }
            
        except Exception as e:
            logger.error(f"Error handling lesson answer: {e}")
            raise OrchestratorError(f"Failed to handle lesson answer: {e}")
    
    async def _handle_welcome_state(
        self, 
        user_id: str, 
        message: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle welcome state in onboarding."""
        # Send welcome message
        response = MessageTemplates.welcome_message()
        await whatsapp_client.send_message(user_id, response)
        
        # Move to language selection
        session["state"] = "language_selection"
        
        # Send language selection menu
        language_menu = MessageTemplates.language_selection_menu()
        await whatsapp_client.send_message(user_id, language_menu)
        
        return {"type": "onboarding", "state": "welcome", "next_state": "language_selection"}
    
    async def _handle_language_selection(
        self, 
        user_id: str, 
        message: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle language selection in onboarding."""
        # Parse language selection
        language_map = {
            "1": "English",
            "2": "French", 
            "3": "Italian",
            "4": "German"
        }
        
        selected_language = language_map.get(message.strip())
        
        if selected_language:
            session["target_language"] = selected_language
            session["state"] = "level_selection"
            
            # Send level selection menu
            level_menu = MessageTemplates.level_selection_menu()
            await whatsapp_client.send_message(user_id, level_menu)
            
            return {
                "type": "onboarding", 
                "state": "language_selection",
                "selected_language": selected_language,
                "next_state": "level_selection"
            }
        else:
            # Invalid selection, ask again
            await whatsapp_client.send_message(
                user_id, 
                "Please select a number from the list (1-4) 📝"
            )
            return {"type": "onboarding", "state": "language_selection", "error": "invalid_selection"}
    
    async def _handle_level_selection(
        self, 
        user_id: str, 
        message: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle level selection in onboarding."""
        level_map = {
            "1": "A1", "2": "A2", "3": "B1", 
            "4": "B2", "5": "C1", "6": "C2"
        }
        
        selected_level = level_map.get(message.strip())
        
        if selected_level:
            session["level"] = selected_level
            session["state"] = "goal_selection"
            
            # Ask about learning goal
            await whatsapp_client.send_message(
                user_id,
                "🎯 What's your main goal?\n\n"
                "1. 🏢 Work/Business\n"
                "2. ✈️ Travel\n"
                "3. 🎓 Academic\n"
                "4. 💬 Social/Personal\n\n"
                "Reply with the number of your choice!"
            )
            
            return {
                "type": "onboarding",
                "state": "level_selection", 
                "selected_level": selected_level,
                "next_state": "goal_selection"
            }
        else:
            await whatsapp_client.send_message(
                user_id,
                "Please select a number from the list (1-6) 📝"
            )
            return {"type": "onboarding", "state": "level_selection", "error": "invalid_selection"}
    
    async def _handle_goal_selection(
        self, 
        user_id: str, 
        message: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle goal selection in onboarding."""
        goal_map = {
            "1": "Work/Business",
            "2": "Travel", 
            "3": "Academic",
            "4": "Social/Personal"
        }
        
        selected_goal = goal_map.get(message.strip())
        
        if selected_goal:
            session["learning_goal"] = selected_goal
            session["state"] = "chat"
            session["is_new_user"] = False
            
            # Send completion message
            await whatsapp_client.send_message(
                user_id,
                f"🎉 Perfect! You're all set up!\n\n"
                f"📚 Level: {session['level']}\n"
                f"🌍 Language: {session['target_language']}\n"
                f"🎯 Goal: {selected_goal}\n\n"
                f"Ready to start learning? Send me a message! 🚀"
            )
            
            return {
                "type": "onboarding_complete",
                "state": "goal_selection",
                "selected_goal": selected_goal
            }
        else:
            await whatsapp_client.send_message(
                user_id,
                "Please select a number from the list (1-4) 📝"
            )
            return {"type": "onboarding", "state": "goal_selection", "error": "invalid_selection"}


# Global chat flow instance
chat_flow = ChatFlow()
