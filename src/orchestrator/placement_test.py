"""Adaptive placement test logic for determining user language level."""

import logging
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from src.data.models import LanguageLevel, ExerciseType, User, UserProgress
from src.data.repositories.exercise import ExerciseRepository
from src.data.repositories.user_progress import UserProgressRepository
from src.data.repositories.user import UserRepository

logger = logging.getLogger(__name__)


@dataclass
class PlacementTestQuestion:
    """Represents a question in the placement test."""
    exercise_id: int
    question: str
    correct_answer: str
    options: Optional[List[str]]
    difficulty: LanguageLevel
    exercise_type: ExerciseType
    points: int
    time_limit_seconds: int


@dataclass
class PlacementTestResult:
    """Result of the placement test."""
    user_id: int
    recommended_level: LanguageLevel
    confidence_score: float
    total_questions: int
    correct_answers: int
    accuracy_percentage: float
    average_response_time_ms: int
    weak_areas: List[str]
    strong_areas: List[str]
    test_duration_ms: int


class AdaptivePlacementTest:
    """Adaptive placement test that adjusts difficulty based on user performance."""
    
    def __init__(self, db_session: Session):
        """
        Initialize the adaptive placement test.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self.exercise_repo = ExerciseRepository(db_session)
        self.progress_repo = UserProgressRepository(db_session)
        self.user_repo = UserRepository(db_session)
        
        # Define difficulty progression
        self.difficulty_order = [
            LanguageLevel.A1,
            LanguageLevel.A2,
            LanguageLevel.B1,
            LanguageLevel.B2
        ]
        
        # Define points per difficulty level
        self.points_by_difficulty = {
            LanguageLevel.A1: 1,
            LanguageLevel.A2: 2,
            LanguageLevel.B1: 3,
            LanguageLevel.B2: 4
        }
        
        # Define time limits by difficulty (seconds)
        self.time_limits = {
            LanguageLevel.A1: 30,
            LanguageLevel.A2: 45,
            LanguageLevel.B1: 60,
            LanguageLevel.B2: 90
        }
    
    def generate_placement_test(
        self,
        user_id: int,
        source_lang: str,
        target_lang: str,
        max_questions: int = 20
    ) -> List[PlacementTestQuestion]:
        """
        Generate an adaptive placement test for a user.
        
        Args:
            user_id: User ID
            source_lang: Source language code
            target_lang: Target language code
            max_questions: Maximum number of questions
            
        Returns:
            List of placement test questions
        """
        logger.info(f"Generating placement test for user {user_id}")
        
        # Get user info
        user = self.user_repo.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if user already has a level
        if user.level and user.level != LanguageLevel.A1:
            logger.info(f"User {user_id} already has level {user.level.value}")
            return []
        
        # Start with A1 level and adapt based on performance
        questions = []
        current_difficulty = LanguageLevel.A1
        consecutive_correct = 0
        consecutive_incorrect = 0
        
        while len(questions) < max_questions:
            # Get exercises for current difficulty
            exercises = self._get_placement_exercises(
                source_lang, target_lang, current_difficulty
            )
            
            if not exercises:
                logger.warning(f"No exercises found for {current_difficulty.value}")
                # Move to next difficulty
                current_index = self.difficulty_order.index(current_difficulty)
                if current_index < len(self.difficulty_order) - 1:
                    current_difficulty = self.difficulty_order[current_index + 1]
                else:
                    break
                continue
            
            # Select random exercise
            exercise = random.choice(exercises)
            
            # Create question
            question = PlacementTestQuestion(
                exercise_id=exercise.id,
                question=exercise.question,
                correct_answer=exercise.correct_answer,
                options=exercise.options,
                difficulty=current_difficulty,
                exercise_type=exercise.exercise_type,
                points=self.points_by_difficulty[current_difficulty],
                time_limit_seconds=self.time_limits[current_difficulty]
            )
            
            questions.append(question)
            
            # Log question for tracking (we'll adapt in real-time during actual test)
            logger.debug(f"Added {current_difficulty.value} question: {question.question[:50]}...")
        
        logger.info(f"Generated {len(questions)} placement test questions")
        return questions
    
    def _get_placement_exercises(
        self,
        source_lang: str,
        target_lang: str,
        difficulty: LanguageLevel,
        count: int = 10
    ) -> List:
        """
        Get exercises for placement test.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            difficulty: Difficulty level
            count: Number of exercises to get
            
        Returns:
            List of exercises
        """
        # Get exercises suitable for placement test
        exercises = self.exercise_repo.get_exercises_for_lesson(
            source_lang=source_lang,
            target_lang=target_lang,
            difficulty=difficulty,
            count=count * 2,  # Get more to have variety
            exercise_types=[ExerciseType.TRANSLATION, ExerciseType.MULTIPLE_CHOICE]
        )
        
        return exercises[:count]
    
    def evaluate_placement_test(
        self,
        user_id: int,
        answers: Dict[int, Dict],  # exercise_id -> {"answer": str, "response_time_ms": int}
        test_start_time_ms: int,
        test_end_time_ms: int
    ) -> PlacementTestResult:
        """
        Evaluate placement test answers and determine user level.
        
        Args:
            user_id: User ID
            answers: Dictionary of exercise answers and response times
            test_start_time_ms: Test start timestamp in milliseconds
            test_end_time_ms: Test end timestamp in milliseconds
            
        Returns:
            Placement test result
        """
        logger.info(f"Evaluating placement test for user {user_id}")
        
        # Get questions (we need to retrieve them from the test data)
        questions = self._get_test_questions(user_id, list(answers.keys()))
        
        total_points = 0
        earned_points = 0
        correct_count = 0
        response_times = []
        difficulty_performance = {level: {"correct": 0, "total": 0} for level in LanguageLevel}
        
        # Evaluate each answer
        for exercise_id, answer_data in answers.items():
            question = next((q for q in questions if q.exercise_id == exercise_id), None)
            if not question:
                continue
            
            is_correct = self._evaluate_answer(question, answer_data["answer"])
            response_time = answer_data.get("response_time_ms", 0)
            
            # Track performance
            if is_correct:
                earned_points += question.points
                correct_count += 1
                difficulty_performance[question.difficulty]["correct"] += 1
            
            difficulty_performance[question.difficulty]["total"] += 1
            total_points += question.points
            response_times.append(response_time)
            
            # Save progress
            self.progress_repo.create_progress(
                user_id=user_id,
                exercise_id=exercise_id,
                is_correct=is_correct,
                user_answer=answer_data["answer"],
                response_time_ms=response_time
            )
        
        # Calculate metrics
        accuracy = (correct_count / len(answers) * 100) if answers else 0
        avg_response_time = sum(response_times) // len(response_times) if response_times else 0
        test_duration = test_end_time_ms - test_start_time_ms
        
        # Determine recommended level
        recommended_level, confidence = self._determine_level(difficulty_performance, accuracy)
        
        # Identify weak and strong areas
        weak_areas, strong_areas = self._analyze_areas(difficulty_performance)
        
        # Create result
        result = PlacementTestResult(
            user_id=user_id,
            recommended_level=recommended_level,
            confidence_score=confidence,
            total_questions=len(answers),
            correct_answers=correct_count,
            accuracy_percentage=accuracy,
            average_response_time_ms=avg_response_time,
            weak_areas=weak_areas,
            strong_areas=strong_areas,
            test_duration_ms=test_duration
        )
        
        # Update user level
        self._update_user_level(user_id, recommended_level)
        
        logger.info(f"Placement test evaluated: {result}")
        return result
    
    def _evaluate_answer(self, question: PlacementTestQuestion, user_answer: str) -> bool:
        """
        Evaluate if user answer is correct.
        
        Args:
            question: The test question
            user_answer: User's answer
            
        Returns:
            True if correct, False otherwise
        """
        # Normalize answers for comparison
        user_answer = user_answer.strip().lower()
        correct_answer = question.correct_answer.strip().lower()
        
        # Exact match
        if user_answer == correct_answer:
            return True
        
        # For multiple choice, check if it matches one of the options
        if question.exercise_type == ExerciseType.MULTIPLE_CHOICE and question.options:
            options = [opt.strip().lower() for opt in question.options]
            if user_answer in options:
                return user_answer == correct_answer
        
        # Fuzzy matching for translation exercises
        if question.exercise_type == ExerciseType.TRANSLATION:
            # Simple fuzzy matching - could be enhanced with more sophisticated algorithms
            return self._fuzzy_match(user_answer, correct_answer)
        
        return False
    
    def _fuzzy_match(self, user_answer: str, correct_answer: str) -> bool:
        """
        Simple fuzzy matching for translation exercises.
        
        Args:
            user_answer: User's answer
            correct_answer: Correct answer
            
        Returns:
            True if close enough match
        """
        # Remove common punctuation and extra spaces
        import re
        user_clean = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïñòóôõöœùúûüýÿ]', '', user_answer, flags=re.IGNORECASE)
        correct_clean = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïñòóôõöœùúûüýÿ]', '', correct_answer, flags=re.IGNORECASE)
        
        # Check if they're exactly the same after cleaning
        if user_clean == correct_clean:
            return True
        
        # Check word overlap (simple approach)
        user_words = set(user_clean.split())
        correct_words = set(correct_clean.split())
        
        if not user_words or not correct_words:
            return False
        
        overlap = len(user_words.intersection(correct_words))
        overlap_ratio = overlap / max(len(user_words), len(correct_words))
        
        # Consider it correct if 80% or more words overlap
        return overlap_ratio >= 0.8
    
    def _determine_level(
        self,
        difficulty_performance: Dict[LanguageLevel, Dict],
        overall_accuracy: float
    ) -> Tuple[LanguageLevel, float]:
        """
        Determine user's recommended level based on performance.
        
        Args:
            difficulty_performance: Performance by difficulty level
            overall_accuracy: Overall accuracy percentage
            
        Returns:
            Tuple of (recommended_level, confidence_score)
        """
        level_scores = {}
        
        for level in LanguageLevel:
            perf = difficulty_performance.get(level)
            if not perf or perf["total"] == 0:
                continue
            
            accuracy = (perf["correct"] / perf["total"] * 100)
            
            # Calculate score based on accuracy and difficulty
            base_score = accuracy
            difficulty_bonus = self.points_by_difficulty[level] * 5
            level_scores[level] = base_score + difficulty_bonus
        
        if not level_scores:
            return LanguageLevel.A1, 0.5
        
        # Find best performing level
        best_level = max(level_scores, key=level_scores.get)
        best_score = level_scores[best_level]
        
        # Calculate confidence based on consistency
        scores = list(level_scores.values())
        if len(scores) > 1:
            score_std = (max(scores) - min(scores)) / max(scores)
            confidence = 1.0 - score_std
        else:
            confidence = 0.7  # Default confidence with limited data
        
        # Adjust confidence based on overall accuracy
        if overall_accuracy >= 80:
            confidence = min(confidence + 0.2, 1.0)
        elif overall_accuracy < 50:
            confidence = max(confidence - 0.2, 0.3)
        
        return best_level, confidence
    
    def _analyze_areas(
        self,
        difficulty_performance: Dict[LanguageLevel, Dict]
    ) -> Tuple[List[str], List[str]]:
        """
        Analyze weak and strong areas based on performance.
        
        Args:
            difficulty_performance: Performance by difficulty level
            
        Returns:
            Tuple of (weak_areas, strong_areas)
        """
        weak_areas = []
        strong_areas = []
        
        for level in LanguageLevel:
            perf = difficulty_performance.get(level)
            if not perf or perf["total"] == 0:
                continue
            
            accuracy = perf["correct"] / perf["total"]
            
            if accuracy >= 0.8:
                strong_areas.append(f"{level.value} level")
            elif accuracy < 0.5:
                weak_areas.append(f"{level.value} level")
        
        return weak_areas, strong_areas
    
    def _update_user_level(self, user_id: int, level: LanguageLevel):
        """
        Update user's language level.
        
        Args:
            user_id: User ID
            level: Recommended level
        """
        user = self.user_repo.get(user_id)
        if user:
            user.level = level
            self.db_session.commit()
            logger.info(f"Updated user {user_id} level to {level.value}")
    
    def _get_test_questions(self, user_id: int, exercise_ids: List[int]) -> List[PlacementTestQuestion]:
        """
        Retrieve test questions from exercise IDs.
        
        Args:
            user_id: User ID
            exercise_ids: List of exercise IDs
            
        Returns:
            List of placement test questions
        """
        questions = []
        
        for exercise_id in exercise_ids:
            exercise = self.exercise_repo.get(exercise_id)
            if exercise:
                question = PlacementTestQuestion(
                    exercise_id=exercise.id,
                    question=exercise.question,
                    correct_answer=exercise.correct_answer,
                    options=exercise.options,
                    difficulty=exercise.difficulty,
                    exercise_type=exercise.exercise_type,
                    points=self.points_by_difficulty[exercise.difficulty],
                    time_limit_seconds=self.time_limits[exercise.difficulty]
                )
                questions.append(question)
        
        return questions
    
    def get_placement_test_history(self, user_id: int) -> List[Dict]:
        """
        Get user's placement test history.
        
        Args:
            user_id: User ID
            
        Returns:
            List of test results
        """
        # This would typically query a test_results table
        # For now, we'll return recent progress as a proxy
        recent_progress = self.progress_repo.get_user_recent_progress(user_id, limit=50)
        
        # Group by test session (simplified approach)
        test_sessions = []
        if recent_progress:
            # Create a summary of recent performance
            correct = sum(1 for p in recent_progress if p.is_correct)
            total = len(recent_progress)
            accuracy = (correct / total * 100) if total > 0 else 0
            
            test_sessions.append({
                "date": recent_progress[0].created_at.isoformat() if recent_progress else None,
                "total_questions": total,
                "correct_answers": correct,
                "accuracy": accuracy,
                "level": "Recent Activity"
            })
        
        return test_sessions
