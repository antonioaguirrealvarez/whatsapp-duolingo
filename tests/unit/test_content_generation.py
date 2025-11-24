"""Unit tests for Content Generation Agent."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session

from src.services.llm.content_generation import ContentGenerationAgent
from src.data.models import LanguageLevel, ExerciseType, ContentGenerationLog, Topic, User
from src.data.repositories.user import UserRepository


class TestContentGenerationAgent:
    """Test suite for ContentGenerationAgent."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=Session)
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        session.query.return_value = MagicMock()
        return session
    
    @pytest.fixture
    def agent(self, mock_session):
        """Create content generation agent with mocked dependencies."""
        with patch('src.services.llm.content_generation.get_settings') as mock_settings, \
             patch('src.services.llm.content_generation.get_langsmith_manager') as mock_langsmith, \
             patch('src.services.llm.content_generation.ChatOpenAI') as mock_llm:
            
            # Mock settings
            settings = MagicMock()
            settings.OPENAI_MODEL = "gpt-4"
            settings.OPENAI_API_KEY = "test-key"
            mock_settings.return_value = settings
            
            # Mock LangSmith manager
            langsmith_manager = MagicMock()
            langsmith_manager.is_enabled.return_value = False
            mock_langsmith.return_value = langsmith_manager
            
            # Create agent
            agent = ContentGenerationAgent(mock_session)
            
            # Mock the generation chain
            agent.generation_chain = AsyncMock()
            
            return agent
    
    @pytest.mark.asyncio
    async def test_generate_exercises_success(self, agent, mock_session):
        """Test successful exercise generation."""
        # Mock LLM response
        mock_response = [
            {
                "question": "How do you say 'hello' in English?",
                "correct_answer": "Hello",
                "options": ["Hola", "Hello", "Bonjour", "Ciao"],
                "explanation": "Common greeting"
            },
            {
                "question": "Translate 'good morning'",
                "correct_answer": "Good morning",
                "options": None,
                "explanation": "Morning greeting"
            }
        ]
        agent.generation_chain.ainvoke.return_value = mock_response
        
        # Mock repositories
        agent.exercise_repo = MagicMock()
        agent.exercise_repo.get_by_field.return_value = None
        agent.exercise_repo.create_exercise.return_value = MagicMock()
        
        # Mock topic creation
        with patch('src.data.models.Topic') as mock_topic:
            mock_topic_instance = MagicMock()
            mock_topic_instance.id = 1
            mock_topic.return_value = mock_topic_instance
            
            result = await agent.generate_exercises(
                source_lang="es",
                target_lang="en",
                difficulty=LanguageLevel.A1,
                exercise_type=ExerciseType.MULTIPLE_CHOICE,
                topic="Greetings",
                count=2,
                save_to_db=True
            )
        
        assert result["success"] is True
        assert result["generated_count"] == 2
        assert result["saved_count"] == 2
        assert len(result["exercises"]) == 2
    
    @pytest.mark.asyncio
    async def test_generate_exercises_llm_failure(self, agent):
        """Test exercise generation when LLM fails."""
        # Mock LLM failure
        agent.generation_chain.ainvoke.side_effect = Exception("LLM error")
        
        result = await agent.generate_exercises(
            source_lang="es",
            target_lang="en",
            difficulty=LanguageLevel.A1,
            exercise_type=ExerciseType.TRANSLATION,
            topic="Greetings",
            count=5
        )
        
        assert result["success"] is False
        assert "error" in result
        assert result["generated_count"] == 0
        assert result["saved_count"] == 0
    
    @pytest.mark.asyncio
    async def test_validate_and_process_exercises(self, agent):
        """Test exercise validation and processing."""
        raw_exercises = [
            {
                "question": "Test question 1",
                "correct_answer": "Test answer 1",
                "options": ["A", "B", "C", "D"],
                "explanation": "Test explanation 1"
            },
            {
                "question": "Test question 2",
                "correct_answer": "Test answer 2",
                # Missing options for non-multiple choice
                "explanation": "Test explanation 2"
            },
            {
                # Missing required fields
                "options": ["A", "B", "C", "D"]
            }
        ]
        
        result = agent._validate_and_process_exercises(
            raw_exercises, "es", "en", LanguageLevel.A1, ExerciseType.MULTIPLE_CHOICE
        )
        
        # Should only include valid exercises
        assert len(result) == 2
        assert result[0]["question"] == "Test question 1"
        assert result[0]["correct_answer"] == "Test answer 1"
        assert result[0]["options"] is not None  # Should be JSON string for multiple choice
        assert result[1]["question"] == "Test question 2"
        assert result[1]["options"] is None  # No options provided
    
    @pytest.mark.asyncio
    async def test_save_exercises(self, agent, mock_session):
        """Test saving exercises to database."""
        exercises = [
            {
                "question": "Test question",
                "correct_answer": "Test answer",
                "options": None,
                "difficulty": LanguageLevel.A1,
                "exercise_type": ExerciseType.TRANSLATION,
                "source_lang": "es",
                "target_lang": "en",
                "explanation": "Test explanation"
            }
        ]
        
        # Mock repositories
        mock_topic = MagicMock()
        mock_topic.id = 1
        agent.exercise_repo = MagicMock()
        agent.exercise_repo.get_by_field.return_value = mock_topic
        agent.exercise_repo.create_exercise.return_value = MagicMock()
        
        result = await agent._save_exercises(exercises, "Test Topic")
        
        assert result == 1
        agent.exercise_repo.create_exercise.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_exercises_create_topic(self, agent, mock_session):
        """Test saving exercises when topic doesn't exist."""
        exercises = [
            {
                "question": "Test question",
                "correct_answer": "Test answer",
                "options": None,
                "difficulty": LanguageLevel.A1,
                "exercise_type": ExerciseType.TRANSLATION,
                "source_lang": "es",
                "target_lang": "en",
                "explanation": "Test explanation"
            }
        ]
        
        # Mock topic doesn't exist
        agent.exercise_repo = MagicMock()
        agent.exercise_repo.get_by_field.return_value = None
        
        # Mock topic creation
        with patch('src.data.models.Topic') as mock_topic_class:
            mock_topic = MagicMock()
            mock_topic.id = 1
            mock_topic_class.return_value = mock_topic
            
            # Mock exercise creation
            agent.exercise_repo = MagicMock()
            agent.exercise_repo.create_exercise.return_value = MagicMock()
            
            result = await agent._save_exercises(exercises, "New Topic")
        
        assert result == 1
        agent.exercise_repo.create_exercise.assert_called_once()
    
    def test_log_generation(self, agent, mock_session):
        """Test logging generation attempts."""
        agent._log_generation(
            source_lang="es",
            target_lang="en",
            topic="Greetings",
            difficulty=LanguageLevel.A1,
            exercise_type=ExerciseType.TRANSLATION,
            requested_count=5,
            generated_count=4,
            accepted_count=3,
            processing_time_ms=1000,
            status="success"
        )
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_lesson_exercises(self, agent, mock_session):
        """Test generating exercises for a specific user's lesson."""
        # Mock user
        mock_user = MagicMock()
        mock_user.native_lang = "es"
        mock_user.target_lang = "en"
        mock_user.level = LanguageLevel.A1
        
        # Mock user repository
        with patch('src.data.repositories.user.UserRepository') as mock_user_repo_class:
            mock_user_repo = MagicMock()
            mock_user_repo.get.return_value = mock_user
            mock_user_repo_class.return_value = mock_user_repo
            
            # Mock generate_exercises
            agent.generate_exercises = AsyncMock(return_value={
                "success": True,
                "exercises": []
            })
            
            # Mock exercise retrieval
            mock_exercise_repo = MagicMock()
            mock_exercise_repo.get_exercises_for_lesson.return_value = [
                MagicMock(id=1), MagicMock(id=2)
            ]
            agent.exercise_repo = mock_exercise_repo
            
            result = await agent.generate_lesson_exercises(
                user_id=1,
                lesson_size=2,
                focus_weak_areas=False
            )
        
        assert len(result) == 2
        agent.generate_exercises.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_lesson_exercises_user_not_found(self, agent, mock_session):
        """Test generating lesson exercises when user doesn't exist."""
        # Mock user repository
        with patch('src.data.repositories.user.UserRepository') as mock_user_repo_class:
            mock_user_repo = MagicMock()
            mock_user_repo.get.return_value = None
            mock_user_repo_class.return_value = mock_user_repo
            
            with pytest.raises(ValueError, match="User 1 not found"):
                await agent.generate_lesson_exercises(
                    user_id=1,
                    lesson_size=5
                )
    
    @pytest.mark.asyncio
    async def test_generate_lesson_exercises_generation_failure(self, agent, mock_session):
        """Test generating lesson exercises when generation fails."""
        # Mock user
        mock_user = MagicMock()
        mock_user.native_lang = "es"
        mock_user.target_lang = "en"
        mock_user.level = LanguageLevel.A1
        
        # Mock user repository
        with patch('src.data.repositories.user.UserRepository') as mock_user_repo_class:
            mock_user_repo = MagicMock()
            mock_user_repo.get.return_value = mock_user
            mock_user_repo_class.return_value = mock_user_repo
            
            # Mock progress repo for weak area analysis
            agent.progress_repo = MagicMock()
            agent.progress_repo.get_user_accuracy_stats.return_value = {
                "error_distribution": {"grammar": 5, "vocabulary": 3}
            }
            
            # Mock generate_exercises failure
            agent.generate_exercises = AsyncMock(return_value={
                "success": False,
                "error": "Generation failed"
            })
            
            with pytest.raises(Exception, match="Failed to generate lesson exercises"):
                await agent.generate_lesson_exercises(
                    user_id=1,
                    lesson_size=5
                )
    
    def test_get_generation_stats(self, agent, mock_session):
        """Test getting generation statistics."""
        # Mock query results
        mock_query = mock_session.query.return_value
        mock_query.count.return_value = 10
        mock_query.filter.return_value.count.return_value = 8
        mock_query.order_by.return_value.limit.return_value.all.return_value = [
            MagicMock(
                topic="Greetings",
                status="success",
                generated_count=5,
                accepted_count=4,
                created_at=MagicMock()
            )
        ]
        
        result = agent.get_generation_stats()
        
        assert result["total_generations"] == 10
        assert result["successful_generations"] == 8
        assert result["success_rate"] == 80.0
        assert len(result["recent_generations"]) == 1
    
    def test_get_generation_stats_error(self, agent, mock_session):
        """Test getting generation stats when error occurs."""
        mock_session.query.side_effect = Exception("Database error")
        
        result = agent.get_generation_stats()
        
        assert "error" in result
