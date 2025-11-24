"""Session manager for maintaining user context and state."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.core.exceptions import SessionError

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions with in-memory storage (MVP)."""
    
    def __init__(self):
        """Initialize the session manager."""
        # In-memory session storage
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Session manager initialized (in-memory storage)")
    
    async def get_or_create_session(self, user_id: str) -> Dict[str, Any]:
        """
        Get existing session or create new one.
        
        Args:
            user_id: User's WhatsApp ID
            
        Returns:
            User session dictionary
        """
        try:
            if user_id not in self._sessions:
                # Create new session
                session = self._create_new_session(user_id)
                self._sessions[user_id] = session
                logger.info(f"Created new session for user {user_id}")
            else:
                # Update last activity
                session = self._sessions[user_id]
                session["last_activity"] = datetime.now(timezone.utc).isoformat()
                logger.debug(f"Retrieved existing session for user {user_id}")
            
            return self._sessions[user_id]
            
        except Exception as e:
            logger.error(f"Error getting/creating session: {e}")
            raise SessionError(f"Failed to get/create session: {e}")
    
    async def update_session(self, user_id: str, session_data: Dict[str, Any]) -> None:
        """
        Update user session data.
        
        Args:
            user_id: User's WhatsApp ID
            session_data: Updated session data
        """
        try:
            if user_id in self._sessions:
                # Update session with new data
                self._sessions[user_id].update(session_data)
                self._sessions[user_id]["last_activity"] = datetime.now(timezone.utc).isoformat()
                logger.debug(f"Updated session for user {user_id}")
            else:
                logger.warning(f"Attempted to update non-existent session for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            raise SessionError(f"Failed to update session: {e}")
    
    async def delete_session(self, user_id: str) -> None:
        """
        Delete user session.
        
        Args:
            user_id: User's WhatsApp ID
        """
        try:
            if user_id in self._sessions:
                del self._sessions[user_id]
                logger.info(f"Deleted session for user {user_id}")
            else:
                logger.warning(f"Attempted to delete non-existent session for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            raise SessionError(f"Failed to delete session: {e}")
    
    async def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active sessions.
        
        Returns:
            Dictionary of all sessions
        """
        return self._sessions.copy()
    
    async def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up expired sessions.
        
        Args:
            max_age_hours: Maximum age of sessions in hours
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
            
            expired_sessions = []
            for user_id, session in self._sessions.items():
                last_activity = datetime.fromisoformat(session["last_activity"]).timestamp()
                if last_activity < cutoff_time:
                    expired_sessions.append(user_id)
            
            # Remove expired sessions
            for user_id in expired_sessions:
                del self._sessions[user_id]
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            return len(expired_sessions)
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0
    
    def _create_new_session(self, user_id: str) -> Dict[str, Any]:
        """
        Create a new user session with default values.
        
        Args:
            user_id: User's WhatsApp ID
            
        Returns:
            New session dictionary
        """
        now = datetime.now(timezone.utc).isoformat()
        
        return {
            "user_id": user_id,
            "created_at": now,
            "last_activity": now,
            "is_new_user": True,
            "level": "A1",
            "native_language": "Portuguese",
            "target_language": "English",
            "learning_goal": "General fluency",
            "country": "Mexico",
            "history": [],
            "streak": 0,
            "lessons_completed": 0,
            "in_lesson": False,
            "current_lesson": None,
            "current_exercise_id": None,
            "current_expected_output": None,
            "preferences": {
                "persona_style": "funny",
                "daily_notification_time": "09:00"
            },
            "state": "welcome"  # Current state in the conversation flow
        }
    
    async def get_session_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> list:
        """
        Get conversation history for a user.
        
        Args:
            user_id: User's WhatsApp ID
            limit: Maximum number of messages to return
            
        Returns:
            List of conversation messages
        """
        try:
            if user_id not in self._sessions:
                return []
            
            history = self._sessions[user_id].get("history", [])
            return history[-limit:] if history else []
            
        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return []
    
    async def add_to_history(
        self, 
        user_id: str, 
        role: str, 
        content: str
    ) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            user_id: User's WhatsApp ID
            role: Message role (user/assistant/system)
            content: Message content
        """
        try:
            if user_id not in self._sessions:
                return
            
            session = self._sessions[user_id]
            history = session.get("history", [])
            
            # Add new message
            history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Keep only last 20 messages
            session["history"] = history[-20:]
            
            logger.debug(f"Added message to history for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding to history: {e}")
    
    async def update_user_level(self, user_id: str, level: str) -> None:
        """
        Update user's language level.
        
        Args:
            user_id: User's WhatsApp ID
            level: New language level (A1, A2, B1, etc.)
        """
        try:
            if user_id in self._sessions:
                self._sessions[user_id]["level"] = level
                logger.info(f"Updated level for user {user_id} to {level}")
            
        except Exception as e:
            logger.error(f"Error updating user level: {e}")
    
    async def increment_streak(self, user_id: str) -> int:
        """
        Increment user's streak counter.
        
        Args:
            user_id: User's WhatsApp ID
            
        Returns:
            New streak count
        """
        try:
            if user_id not in self._sessions:
                return 0
            
            session = self._sessions[user_id]
            current_streak = session.get("streak", 0)
            new_streak = current_streak + 1
            session["streak"] = new_streak
            
            logger.info(f"Incremented streak for user {user_id} to {new_streak}")
            return new_streak
            
        except Exception as e:
            logger.error(f"Error incrementing streak: {e}")
            return 0
    
    async def increment_lessons_completed(self, user_id: str) -> int:
        """
        Increment user's lessons completed counter.
        
        Args:
            user_id: User's WhatsApp ID
            
        Returns:
            New lessons completed count
        """
        try:
            if user_id not in self._sessions:
                return 0
            
            session = self._sessions[user_id]
            current_count = session.get("lessons_completed", 0)
            new_count = current_count + 1
            session["lessons_completed"] = new_count
            
            logger.info(f"Incremented lessons for user {user_id} to {new_count}")
            return new_count
            
        except Exception as e:
            logger.error(f"Error incrementing lessons: {e}")
            return 0
