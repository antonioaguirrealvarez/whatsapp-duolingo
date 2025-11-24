"""Content generation agent for creating learning exercises."""

import json
import logging
import time
from typing import Dict, List, Optional, Any

from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

from src.core.config import get_settings
from src.data.models import Exercise, LanguageLevel, ExerciseType, ContentGenerationLog
from src.data.repositories.exercise import ExerciseRepository
from src.data.repositories.user_progress import UserProgressRepository
from src.services.llm.langsmith_client import get_langsmith_manager

logger = logging.getLogger(__name__)


class ContentGenerationAgent:
    """Agent for generating educational content using LLMs."""
    
    def __init__(self, db_session):
        """
        Initialize the content generation agent.
        
        Args:
            db_session: Database session for repositories
        """
        self.settings = get_settings()
        self.db_session = db_session
        self.exercise_repo = ExerciseRepository(db_session)
        self.progress_repo = UserProgressRepository(db_session)
        self.langsmith_manager = get_langsmith_manager()
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.settings.OPENAI_MODEL,
            temperature=0.7,
            api_key=self.settings.OPENAI_API_KEY
        )
        
        # Create generation chain
        self._create_generation_chain()
    
    def _create_generation_chain(self):
        """Create the content generation chain."""
        generation_prompt = PromptTemplate.from_template("""
You are an expert language learning content creator. Generate educational exercises for language learners.

Generate {count} exercises for the following specifications:
- Source Language: {source_lang}
- Target Language: {target_lang}
- Difficulty Level: {difficulty}
- Exercise Type: {exercise_type}
- Topic: {topic}

For each exercise, provide:
1. A clear question in the source language
2. The correct answer in the target language
3. Multiple choice options (if applicable) in JSON array format
4. Brief explanation of the learning concept

Requirements:
- Questions must be appropriate for the {difficulty} level (CEFR)
- Content should be culturally appropriate and engaging
- For translation exercises, focus on common phrases and vocabulary
- For multiple choice, provide 4 options with one correct answer
- For fill-in-blank, create sentences with clear context

Output format: JSON array with objects containing:
{{
    "question": "question text",
    "correct_answer": "correct answer",
    "options": ["option1", "option2", "option3", "option4"] or null,
    "explanation": "brief explanation"
}}

Generate exactly {count} exercises:
""")
        
        self.generation_chain = (
            RunnablePassthrough.assign()
            | generation_prompt
            | self.llm
            | JsonOutputParser()
        )
    
    async def generate_exercises(
        self,
        source_lang: str,
        target_lang: str,
        difficulty: LanguageLevel,
        exercise_type: ExerciseType,
        topic: str,
        count: int = 10,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Generate exercises using LLM.
        
        Args:
            source_lang: Source language code (e.g., "es")
            target_lang: Target language code (e.g., "en")
            difficulty: CEFR difficulty level
            exercise_type: Type of exercise to generate
            topic: Topic for the exercises
            count: Number of exercises to generate
            save_to_db: Whether to save exercises to database
            
        Returns:
            Dictionary with generation results
        """
        start_time = time.time()
        
        try:
            # Log generation start
            logger.info(f"Starting content generation: {source_lang}->{target_lang}, {difficulty.value}, {exercise_type.value}")
            
            # Prepare input for LLM
            input_data = {
                "source_lang": source_lang,
                "target_lang": target_lang,
                "difficulty": difficulty.value,
                "exercise_type": exercise_type.value,
                "topic": topic,
                "count": count
            }
            
            # Generate content
            result = await self.generation_chain.ainvoke(input_data)
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Validate and process results
            exercises = self._validate_and_process_exercises(
                result, source_lang, target_lang, difficulty, exercise_type
            )
            
            # Save to database if requested
            saved_count = 0
            if save_to_db:
                saved_count = await self._save_exercises(exercises, topic)
            
            # Log generation completion
            self._log_generation(
                source_lang, target_lang, topic, difficulty, 
                exercise_type, count, len(exercises), saved_count,
                processing_time_ms, "success"
            )
            
            # Trace LLM call
            if self.langsmith_manager.is_enabled():
                self.langsmith_manager.trace_llm_call(
                    model_name=self.settings.OPENAI_MODEL,
                    prompt=str(input_data),
                    response=json.dumps(result),
                    tokens_used=None,  # Would need to calculate this
                    latency_ms=processing_time_ms,
                    metadata={
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "difficulty": difficulty.value,
                        "exercise_type": exercise_type.value,
                        "topic": topic
                    }
                )
            
            return {
                "success": True,
                "exercises": exercises,
                "generated_count": len(exercises),
                "saved_count": saved_count,
                "processing_time_ms": processing_time_ms
            }
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            # Log generation failure
            self._log_generation(
                source_lang, target_lang, topic, difficulty,
                exercise_type, count, 0, 0, processing_time_ms, "failed", error_msg
            )
            
            logger.error(f"Content generation failed: {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "generated_count": 0,
                "saved_count": 0,
                "processing_time_ms": processing_time_ms
            }
    
    def _validate_and_process_exercises(
        self,
        raw_exercises: List[Dict],
        source_lang: str,
        target_lang: str,
        difficulty: LanguageLevel,
        exercise_type: ExerciseType
    ) -> List[Dict]:
        """
        Validate and process generated exercises.
        
        Args:
            raw_exercises: Raw exercises from LLM
            source_lang: Source language code
            target_lang: Target language code
            difficulty: Difficulty level
            exercise_type: Exercise type
            
        Returns:
            List of validated exercises
        """
        validated_exercises = []
        
        for i, exercise in enumerate(raw_exercises):
            try:
                # Validate required fields
                if not all(key in exercise for key in ["question", "correct_answer"]):
                    logger.warning(f"Exercise {i+1} missing required fields, skipping")
                    continue
                
                # Validate question and answer
                if not exercise["question"] or not exercise["correct_answer"]:
                    logger.warning(f"Exercise {i+1} has empty question or answer, skipping")
                    continue
                
                # Process options for multiple choice
                options = None
                if exercise_type == ExerciseType.MULTIPLE_CHOICE:
                    if "options" in exercise and isinstance(exercise["options"], list):
                        # Ensure we have exactly 4 options
                        options_list = exercise["options"][:4]
                        if len(options_list) < 4:
                            # Add dummy options if needed
                            while len(options_list) < 4:
                                options_list.append(f"Option {len(options_list) + 1}")
                        options = json.dumps(options_list)
                
                # Create validated exercise
                validated_exercise = {
                    "question": exercise["question"].strip(),
                    "correct_answer": exercise["correct_answer"].strip(),
                    "options": options,
                    "difficulty": difficulty,
                    "exercise_type": exercise_type,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "explanation": exercise.get("explanation", "").strip()
                }
                
                validated_exercises.append(validated_exercise)
                
            except Exception as e:
                logger.warning(f"Error validating exercise {i+1}: {str(e)}")
                continue
        
        return validated_exercises
    
    async def _save_exercises(self, exercises: List[Dict], topic: str) -> int:
        """
        Save exercises to database.
        
        Args:
            exercises: List of exercises to save
            topic: Topic name for the exercises
            
        Returns:
            Number of exercises saved
        """
        saved_count = 0
        
        # Get or create topic
        topic_obj = self.exercise_repo.get_by_field("name", topic)
        if not topic_obj:
            from src.data.models import Topic
            topic_obj = Topic(name=topic, description=f"Exercises about {topic}")
            self.db_session.add(topic_obj)
            self.db_session.commit()
            self.db_session.refresh(topic_obj)
        
        # Save exercises
        for exercise_data in exercises:
            try:
                exercise_data["topic_id"] = topic_obj.id
                self.exercise_repo.create_exercise(**exercise_data)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving exercise: {str(e)}")
                continue
        
        return saved_count
    
    def _log_generation(
        self,
        source_lang: str,
        target_lang: str,
        topic: str,
        difficulty: LanguageLevel,
        exercise_type: ExerciseType,
        requested_count: int,
        generated_count: int,
        accepted_count: int,
        processing_time_ms: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """
        Log content generation attempt.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            topic: Topic name
            difficulty: Difficulty level
            exercise_type: Exercise type
            requested_count: Number of exercises requested
            generated_count: Number of exercises generated
            accepted_count: Number of exercises accepted
            processing_time_ms: Processing time in milliseconds
            status: Generation status ("success", "partial", "failed")
            error_message: Error message if failed
        """
        try:
            log_data = {
                "source_lang": source_lang,
                "target_lang": target_lang,
                "topic": topic,
                "level": difficulty,
                "exercise_type": exercise_type,
                "count": requested_count,
                "generated_count": generated_count,
                "accepted_count": accepted_count,
                "status": status,
                "error_message": error_message,
                "processing_time_ms": processing_time_ms
            }
            
            # Create log entry
            log_entry = ContentGenerationLog(**log_data)
            self.db_session.add(log_entry)
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Error logging generation: {str(e)}")
    
    async def generate_lesson_exercises(
        self,
        user_id: int,
        lesson_size: int = 10,
        focus_weak_areas: bool = True
    ) -> List[Exercise]:
        """
        Generate exercises for a specific user's lesson.
        
        Args:
            user_id: User ID
            lesson_size: Number of exercises in the lesson
            focus_weak_areas: Whether to focus on user's weak areas
            
        Returns:
            List of exercises for the lesson
        """
        # Get user's learning preferences
        from src.data.repositories.user import UserRepository
        user_repo = UserRepository(self.db_session)
        user = user_repo.get(user_id)
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Analyze user's weak areas if requested
        exercise_types = None
        if focus_weak_areas:
            accuracy_stats = self.progress_repo.get_user_accuracy_stats(user_id)
            error_distribution = accuracy_stats.get("error_distribution", {})
            
            # Focus on areas with most errors
            if error_distribution:
                # Map error types to exercise types
                error_to_exercise = {
                    "grammar": ExerciseType.FILL_IN_BLANK,
                    "vocabulary": ExerciseType.TRANSLATION,
                    "spelling": ExerciseType.MULTIPLE_CHOICE,
                    "syntax": ExerciseType.FILL_IN_BLANK
                }
                
                most_common_error = max(error_distribution, key=error_distribution.get)
                exercise_types = [error_to_exercise.get(most_common_error, ExerciseType.TRANSLATION)]
        
        # Generate exercises
        result = await self.generate_exercises(
            source_lang=user.native_lang or "es",
            target_lang=user.target_lang or "en",
            difficulty=user.level or LanguageLevel.A1,
            exercise_type=exercise_types[0] if exercise_types else ExerciseType.TRANSLATION,
            topic="General Practice",
            count=lesson_size,
            save_to_db=True
        )
        
        if result["success"]:
            # Get the newly created exercises
            exercises = self.exercise_repo.get_exercises_for_lesson(
                source_lang=user.native_lang or "es",
                target_lang=user.target_lang or "en",
                difficulty=user.level or LanguageLevel.A1,
                count=lesson_size,
                exercise_types=exercise_types
            )
            return exercises
        
        raise Exception(f"Failed to generate lesson exercises: {result.get('error', 'Unknown error')}")
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """
        Get content generation statistics.
        
        Returns:
            Dictionary with generation statistics
        """
        try:
            # Query generation logs
            total_generations = self.db_session.query(ContentGenerationLog).count()
            successful_generations = (
                self.db_session.query(ContentGenerationLog)
                .filter(ContentGenerationLog.status == "success")
                .count()
            )
            
            # Get recent generations
            recent_generations = (
                self.db_session.query(ContentGenerationLog)
                .order_by(ContentGenerationLog.created_at.desc())
                .limit(10)
                .all()
            )
            
            return {
                "total_generations": total_generations,
                "successful_generations": successful_generations,
                "success_rate": (successful_generations / total_generations * 100) if total_generations > 0 else 0,
                "recent_generations": [
                    {
                        "topic": gen.topic,
                        "status": gen.status,
                        "generated_count": gen.generated_count,
                        "accepted_count": gen.accepted_count,
                        "created_at": gen.created_at.isoformat()
                    }
                    for gen in recent_generations
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting generation stats: {str(e)}")
            return {"error": str(e)}
