"""Exercise repository for managing learning exercises."""

from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.data.models import Exercise, LanguageLevel, ExerciseType, Topic
from src.data.repositories.base import BaseRepository


class ExerciseRepository(BaseRepository[Exercise]):
    """Repository for Exercise model operations."""
    
    def __init__(self, db_session: Session):
        """Initialize exercise repository."""
        super().__init__(Exercise, db_session)
    
    def get_by_language_pair(
        self,
        source_lang: str,
        target_lang: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Exercise]:
        """
        Get exercises for a specific language pair.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of exercises matching the language pair
        """
        return (
            self.db.query(Exercise)
            .filter(
                and_(
                    Exercise.source_lang == source_lang,
                    Exercise.target_lang == target_lang
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_difficulty(
        self,
        difficulty: LanguageLevel,
        skip: int = 0,
        limit: int = 100
    ) -> List[Exercise]:
        """
        Get exercises by difficulty level.
        
        Args:
            difficulty: Language proficiency level
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of exercises at the specified difficulty
        """
        return self.get_multi_by_field("difficulty", difficulty, skip, limit)
    
    def get_by_type(
        self,
        exercise_type: ExerciseType,
        skip: int = 0,
        limit: int = 100
    ) -> List[Exercise]:
        """
        Get exercises by type.
        
        Args:
            exercise_type: Type of exercise
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of exercises of the specified type
        """
        return self.get_multi_by_field("exercise_type", exercise_type, skip, limit)
    
    def get_by_topic(
        self,
        topic_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Exercise]:
        """
        Get exercises for a specific topic.
        
        Args:
            topic_id: Topic ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of exercises for the topic
        """
        return self.get_multi_by_field("topic_id", topic_id, skip, limit)
    
    def search_exercises(
        self,
        query: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        difficulty: Optional[LanguageLevel] = None,
        exercise_type: Optional[ExerciseType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Exercise]:
        """
        Search exercises by question text with optional filters.
        
        Args:
            query: Search query string
            source_lang: Filter by source language
            target_lang: Filter by target language
            difficulty: Filter by difficulty level
            exercise_type: Filter by exercise type
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching exercises
        """
        db_query = self.db.query(Exercise).filter(
            Exercise.question.contains(query)
        )
        
        if source_lang:
            db_query = db_query.filter(Exercise.source_lang == source_lang)
        if target_lang:
            db_query = db_query.filter(Exercise.target_lang == target_lang)
        if difficulty:
            db_query = db_query.filter(Exercise.difficulty == difficulty)
        if exercise_type:
            db_query = db_query.filter(Exercise.exercise_type == exercise_type)
        
        return db_query.offset(skip).limit(limit).all()
    
    def get_random_exercises(
        self,
        count: int = 10,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        difficulty: Optional[LanguageLevel] = None,
        exercise_type: Optional[ExerciseType] = None
    ) -> List[Exercise]:
        """
        Get random exercises with optional filters.
        
        Args:
            count: Number of exercises to return
            source_lang: Filter by source language
            target_lang: Filter by target language
            difficulty: Filter by difficulty level
            exercise_type: Filter by exercise type
            
        Returns:
            List of random exercises
        """
        db_query = self.db.query(Exercise)
        
        if source_lang:
            db_query = db_query.filter(Exercise.source_lang == source_lang)
        if target_lang:
            db_query = db_query.filter(Exercise.target_lang == target_lang)
        if difficulty:
            db_query = db_query.filter(Exercise.difficulty == difficulty)
        if exercise_type:
            db_query = db_query.filter(Exercise.exercise_type == exercise_type)
        
        # Use ORDER BY RANDOM() for SQLite
        return db_query.order_by(self.db.sql.func.random()).limit(count).all()
    
    def create_exercise(
        self,
        question: str,
        correct_answer: str,
        difficulty: LanguageLevel,
        exercise_type: ExerciseType,
        source_lang: str,
        target_lang: str,
        options: Optional[str] = None,
        topic_id: Optional[int] = None
    ) -> Exercise:
        """
        Create a new exercise.
        
        Args:
            question: Exercise question
            correct_answer: Correct answer
            difficulty: Difficulty level
            exercise_type: Type of exercise
            source_lang: Source language code
            target_lang: Target language code
            options: JSON string for multiple choice options
            topic_id: Optional topic ID
            
        Returns:
            Created exercise instance
        """
        exercise_data = {
            "question": question,
            "correct_answer": correct_answer,
            "difficulty": difficulty,
            "exercise_type": exercise_type,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "options": options,
            "topic_id": topic_id
        }
        return self.create(exercise_data)
    
    def count_by_language_pair(self, source_lang: str, target_lang: str) -> int:
        """
        Count exercises for a specific language pair.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Number of exercises matching the language pair
        """
        return (
            self.db.query(Exercise)
            .filter(
                and_(
                    Exercise.source_lang == source_lang,
                    Exercise.target_lang == target_lang
                )
            )
            .count()
        )
    
    def count_by_difficulty(self, difficulty: LanguageLevel) -> int:
        """
        Count exercises by difficulty level.
        
        Args:
            difficulty: Difficulty level
            
        Returns:
            Number of exercises at the specified difficulty
        """
        return self.count_by_field("difficulty", difficulty)
    
    def get_exercises_for_lesson(
        self,
        source_lang: str,
        target_lang: str,
        difficulty: LanguageLevel,
        count: int = 10,
        exercise_types: Optional[List[ExerciseType]] = None
    ) -> List[Exercise]:
        """
        Get exercises suitable for a lesson.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            difficulty: Difficulty level
            count: Number of exercises to return
            exercise_types: List of exercise types to include
            
        Returns:
            List of exercises for the lesson
        """
        db_query = self.db.query(Exercise).filter(
            and_(
                Exercise.source_lang == source_lang,
                Exercise.target_lang == target_lang,
                Exercise.difficulty == difficulty
            )
        )
        
        if exercise_types:
            db_query = db_query.filter(
                Exercise.exercise_type.in_(exercise_types)
            )
        
        return db_query.order_by(self.db.sql.func.random()).limit(count).all()
