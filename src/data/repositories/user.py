"""User repository for WhatsApp user management."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from src.data.models import User, LanguageLevel
from src.data.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""
    
    def __init__(self, db_session: Session):
        """Initialize user repository."""
        super().__init__(User, db_session)
    
    def get_by_wa_id(self, wa_id: str) -> Optional[User]:
        """
        Get user by WhatsApp ID.
        
        Args:
            wa_id: WhatsApp user ID
            
        Returns:
            User instance or None if not found
        """
        return self.get_by_field("wa_id", wa_id)
    
    def create_user(
        self,
        wa_id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        native_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        level: Optional[LanguageLevel] = None,
        is_premium: bool = False
    ) -> User:
        """
        Create a new user.
        
        Args:
            wa_id: WhatsApp user ID
            name: User's name
            phone: Phone number
            native_lang: Native language code
            target_lang: Target language code
            level: Language proficiency level
            is_premium: Whether user has premium features
            
        Returns:
            Created user instance
        """
        user_data = {
            "wa_id": wa_id,
            "name": name,
            "phone": phone,
            "native_lang": native_lang,
            "target_lang": target_lang,
            "level": level,
            "is_premium": is_premium,
            "daily_lessons_count": 0,
            "streak_days": 0
        }
        return self.create(user_data)
    
    def update_learning_preferences(
        self,
        user: User,
        native_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        level: Optional[LanguageLevel] = None
    ) -> User:
        """
        Update user's learning preferences.
        
        Args:
            user: User instance to update
            native_lang: Native language code
            target_lang: Target language code
            level: Language proficiency level
            
        Returns:
            Updated user instance
        """
        update_data = {}
        if native_lang is not None:
            update_data["native_lang"] = native_lang
        if target_lang is not None:
            update_data["target_lang"] = target_lang
        if level is not None:
            update_data["level"] = level
        
        return self.update(user, update_data)
    
    def increment_daily_lessons(self, user: User) -> User:
        """
        Increment user's daily lesson count.
        
        Args:
            user: User instance
            
        Returns:
            Updated user instance
        """
        return self.update(user, {"daily_lessons_count": user.daily_lessons_count + 1})
    
    def update_streak(self, user: User, streak_days: int) -> User:
        """
        Update user's streak days.
        
        Args:
            user: User instance
            streak_days: New streak days count
            
        Returns:
            Updated user instance
        """
        update_data = {
            "streak_days": streak_days,
            "last_lesson_date": datetime.utcnow()
        }
        return self.update(user, update_data)
    
    def get_active_users(self, days: int = 7) -> List[User]:
        """
        Get users who have been active in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of active users
        """
        cutoff_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
        
        return (
            self.db.query(User)
            .filter(
                and_(
                    User.last_lesson_date is not None,
                    User.last_lesson_date > datetime.fromtimestamp(cutoff_date)
                )
            )
            .order_by(desc(User.last_lesson_date))
            .all()
        )
    
    def get_premium_users(self) -> List[User]:
        """
        Get all premium users.
        
        Returns:
            List of premium users
        """
        return self.get_multi_by_field("is_premium", True)
    
    def get_users_by_language_pair(
        self,
        native_lang: str,
        target_lang: str
    ) -> List[User]:
        """
        Get users learning a specific language pair.
        
        Args:
            native_lang: Native language code
            target_lang: Target language code
            
        Returns:
            List of users matching the language pair
        """
        return (
            self.db.query(User)
            .filter(
                and_(
                    User.native_lang == native_lang,
                    User.target_lang == target_lang
                )
            )
            .all()
        )
    
    def get_users_by_level(self, level: LanguageLevel) -> List[User]:
        """
        Get users at a specific proficiency level.
        
        Returns:
            List of users at the specified level
        """
        return self.get_multi_by_field("level", level)
    
    def get_top_streak_users(self, limit: int = 10) -> List[User]:
        """
        Get users with the highest streaks.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of users ordered by streak days (descending)
        """
        return (
            self.db.query(User)
            .filter(User.streak_days > 0)
            .order_by(desc(User.streak_days))
            .limit(limit)
            .all()
        )
    
    def get_or_create_user(self, wa_id: str, **kwargs) -> tuple[User, bool]:
        """
        Get existing user or create a new one.
        
        Args:
            wa_id: WhatsApp user ID
            **kwargs: Additional user fields
            
        Returns:
            Tuple of (user instance, created_flag)
        """
        user = self.get_by_wa_id(wa_id)
        if user:
            return user, False
        
        user = self.create_user(wa_id=wa_id, **kwargs)
        return user, True
