"""UserProgress repository for tracking user exercise performance."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from src.data.models import UserProgress, Exercise, ErrorType
from src.data.repositories.base import BaseRepository


class UserProgressRepository(BaseRepository[UserProgress]):
    """Repository for UserProgress model operations."""
    
    def __init__(self, db_session: Session):
        """Initialize user progress repository."""
        super().__init__(UserProgress, db_session)
    
    def get_user_progress(
        self,
        user_id: int,
        exercise_id: int
    ) -> Optional[UserProgress]:
        """
        Get user's progress for a specific exercise.
        
        Args:
            user_id: User ID
            exercise_id: Exercise ID
            
        Returns:
            UserProgress instance or None if not found
        """
        return (
            self.db.query(UserProgress)
            .filter(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.exercise_id == exercise_id
                )
            )
            .first()
        )
    
    def create_progress(
        self,
        user_id: int,
        exercise_id: int,
        is_correct: bool,
        user_answer: str,
        error_type: Optional[ErrorType] = None,
        feedback_key: Optional[str] = None,
        feedback_message: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        attempts: int = 1
    ) -> UserProgress:
        """
        Create a new user progress record.
        
        Args:
            user_id: User ID
            exercise_id: Exercise ID
            is_correct: Whether the answer was correct
            user_answer: User's answer
            error_type: Type of error if incorrect
            feedback_key: Feedback key for error type
            feedback_message: Detailed feedback message
            response_time_ms: Time taken to answer in milliseconds
            attempts: Number of attempts
            
        Returns:
            Created UserProgress instance
        """
        progress_data = {
            "user_id": user_id,
            "exercise_id": exercise_id,
            "is_correct": is_correct,
            "user_answer": user_answer,
            "error_type": error_type,
            "feedback_key": feedback_key,
            "feedback_message": feedback_message,
            "response_time_ms": response_time_ms,
            "attempts": attempts
        }
        return self.create(progress_data)
    
    def update_progress(
        self,
        progress: UserProgress,
        is_correct: bool,
        user_answer: str,
        error_type: Optional[ErrorType] = None,
        feedback_key: Optional[str] = None,
        feedback_message: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ) -> UserProgress:
        """
        Update existing user progress.
        
        Args:
            progress: Existing UserProgress instance
            is_correct: Whether the answer was correct
            user_answer: User's answer
            error_type: Type of error if incorrect
            feedback_key: Feedback key for error type
            feedback_message: Detailed feedback message
            response_time_ms: Time taken to answer in milliseconds
            
        Returns:
            Updated UserProgress instance
        """
        update_data = {
            "is_correct": is_correct,
            "user_answer": user_answer,
            "attempts": progress.attempts + 1
        }
        
        if error_type is not None:
            update_data["error_type"] = error_type
        if feedback_key is not None:
            update_data["feedback_key"] = feedback_key
        if feedback_message is not None:
            update_data["feedback_message"] = feedback_message
        if response_time_ms is not None:
            update_data["response_time_ms"] = response_time_ms
        
        return self.update(progress, update_data)
    
    def get_user_all_progress(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserProgress]:
        """
        Get all progress records for a user.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of user's progress records
        """
        return self.get_multi_by_field("user_id", user_id, skip, limit)
    
    def get_user_correct_answers(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserProgress]:
        """
        Get user's correct answers.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of correct answer records
        """
        return (
            self.db.query(UserProgress)
            .filter(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.is_correct == True
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_user_errors(
        self,
        user_id: int,
        error_type: Optional[ErrorType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserProgress]:
        """
        Get user's errors.
        
        Args:
            user_id: User ID
            error_type: Filter by specific error type
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of error records
        """
        query = self.db.query(UserProgress).filter(
            and_(
                UserProgress.user_id == user_id,
                UserProgress.is_correct == False
            )
        )
        
        if error_type:
            query = query.filter(UserProgress.error_type == error_type)
        
        return query.offset(skip).limit(limit).all()
    
    def get_user_accuracy_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's accuracy statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with accuracy statistics
        """
        total = self.count_by_field("user_id", user_id)
        correct = len(self.get_user_correct_answers(user_id))
        
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Get error type distribution
        error_stats = (
            self.db.query(
                UserProgress.error_type,
                func.count(UserProgress.id).label('count')
            )
            .filter(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.is_correct == False,
                    UserProgress.error_type is not None
                )
            )
            .group_by(UserProgress.error_type)
            .all()
        )
        
        error_distribution = {
            error_type.value: count for error_type, count in error_stats
        }
        
        # Get average response time
        avg_response_time = (
            self.db.query(func.avg(UserProgress.response_time_ms))
            .filter(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.response_time_ms is not None
                )
            )
            .scalar()
        )
        
        return {
            "total_exercises": total,
            "correct_answers": correct,
            "accuracy_percentage": round(accuracy, 2),
            "error_distribution": error_distribution,
            "average_response_time_ms": round(avg_response_time or 0, 2)
        }
    
    def get_user_recent_progress(
        self,
        user_id: int,
        days: int = 7
    ) -> List[UserProgress]:
        """
        Get user's recent progress within the last N days.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of recent progress records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return (
            self.db.query(UserProgress)
            .filter(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.created_at >= cutoff_date
                )
            )
            .order_by(desc(UserProgress.created_at))
            .all()
        )
    
    def get_exercise_performance(
        self,
        exercise_id: int
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a specific exercise.
        
        Args:
            exercise_id: Exercise ID
            
        Returns:
            Dictionary with exercise performance stats
        """
        total = self.count_by_field("exercise_id", exercise_id)
        correct = (
            self.db.query(UserProgress)
            .filter(
                and_(
                    UserProgress.exercise_id == exercise_id,
                    UserProgress.is_correct == True
                )
            )
            .count()
        )
        
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Get common errors
        common_errors = (
            self.db.query(
                UserProgress.error_type,
                func.count(UserProgress.id).label('count')
            )
            .filter(
                and_(
                    UserProgress.exercise_id == exercise_id,
                    UserProgress.is_correct == False,
                    UserProgress.error_type is not None
                )
            )
            .group_by(UserProgress.error_type)
            .order_by(desc('count'))
            .limit(5)
            .all()
        )
        
        return {
            "total_attempts": total,
            "correct_attempts": correct,
            "accuracy_percentage": round(accuracy, 2),
            "common_errors": [
                {"error_type": error_type.value, "count": count}
                for error_type, count in common_errors
            ]
        }
    
    def get_or_create_progress(
        self,
        user_id: int,
        exercise_id: int,
        is_correct: bool,
        user_answer: str,
        **kwargs
    ) -> tuple[UserProgress, bool]:
        """
        Get existing progress or create a new one.
        
        Args:
            user_id: User ID
            exercise_id: Exercise ID
            is_correct: Whether the answer was correct
            user_answer: User's answer
            **kwargs: Additional progress fields
            
        Returns:
            Tuple of (progress instance, created_flag)
        """
        progress = self.get_user_progress(user_id, exercise_id)
        
        if progress:
            # Update existing progress
            updated_progress = self.update_progress(
                progress, is_correct, user_answer, **kwargs
            )
            return updated_progress, False
        else:
            # Create new progress
            new_progress = self.create_progress(
                user_id, exercise_id, is_correct, user_answer, **kwargs
            )
            return new_progress, True
