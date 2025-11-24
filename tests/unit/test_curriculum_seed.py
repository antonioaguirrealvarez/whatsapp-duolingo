"""Unit tests for Curriculum Seed Generator."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session

from src.orchestrator.curriculum_seed import CurriculumSeedGenerator
from src.data.models import LanguageLevel, ExerciseType, Topic, User


class TestCurriculumSeedGenerator:
    """Test suite for CurriculumSeedGenerator."""
    
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
    def generator(self, mock_session):
        """Create curriculum seed generator with mocked dependencies."""
        with patch('src.orchestrator.curriculum_seed.ExerciseRepository') as mock_exercise_repo, \
             patch('src.orchestrator.curriculum_seed.UserRepository') as mock_user_repo, \
             patch('src.orchestrator.curriculum_seed.ContentGenerationAgent') as mock_content_agent:
            
            # Create generator
            generator = CurriculumSeedGenerator(mock_session)
            
            # Mock repositories
            generator.exercise_repo = mock_exercise_repo.return_value
            generator.user_repo = mock_user_repo.return_value
            generator.content_agent = mock_content_agent.return_value
            
            return generator
    
    @pytest.mark.asyncio
    async def test_generate_full_curriculum(self, generator):
        """Test full curriculum generation."""
        # Mock existing content count
        generator.exercise_repo.count_by_language_pair.return_value = 100
        
        # Mock content generation
        generator.content_agent.generate_exercises = AsyncMock(return_value={
            "success": True,
            "generated_count": 20,
            "saved_count": 20,
            "processing_time_ms": 1000
        })
        
        result = await generator.generate_full_curriculum(
            exercises_per_topic=5,
            max_concurrent_generations=2
        )
        
        assert result["total_generations"] > 0
        assert result["successful_generations"] > 0
        assert result["total_exercises_generated"] > 0
        assert "language_pairs" in result
    
    @pytest.mark.asyncio
    async def test_generate_topic_exercises_success(self, generator):
        """Test successful topic exercise generation."""
        # Mock existing content count
        generator.exercise_repo.count_by_language_pair.return_value = 100
        
        # Mock content generation
        generator.content_agent.generate_exercises = AsyncMock(return_value={
            "success": True,
            "generated_count": 10,
            "saved_count": 10
        })
        
        # Create semaphore
        import asyncio
        semaphore = asyncio.Semaphore(1)
        
        result = await generator._generate_topic_exercises(
            semaphore, "es", "en", LanguageLevel.A1, 
            "Greetings", ExerciseType.TRANSLATION, 10
        )
        
        assert result["success"] is True
        assert result["generated_count"] == 10
        assert result["source_lang"] == "es"
        assert result["target_lang"] == "en"
        assert result["level"] == "A1"
        assert result["topic"] == "Greetings"
        assert result["exercise_type"] == "translation"
    
    @pytest.mark.asyncio
    async def test_generate_topic_exercises_skip_existing(self, generator):
        """Test skipping generation when enough content exists."""
        # Mock existing content count (high enough to skip)
        generator.exercise_repo.count_by_language_pair.return_value = 2000
        
        # Create semaphore
        import asyncio
        semaphore = asyncio.Semaphore(1)
        
        result = await generator._generate_topic_exercises(
            semaphore, "es", "en", LanguageLevel.A1, 
            "Greetings", ExerciseType.TRANSLATION, 10
        )
        
        assert result["success"] is True
        assert result["generated_count"] == 0
        assert result["skipped"] is True
    
    @pytest.mark.asyncio
    async def test_generate_topic_exercises_failure(self, generator):
        """Test topic exercise generation failure."""
        # Mock existing content count
        generator.exercise_repo.count_by_language_pair.return_value = 100
        
        # Mock content generation failure
        generator.content_agent.generate_exercises = AsyncMock(return_value={
            "success": False,
            "error": "Generation failed",
            "generated_count": 0,
            "saved_count": 0
        })
        
        # Create semaphore
        import asyncio
        semaphore = asyncio.Semaphore(1)
        
        result = await generator._generate_topic_exercises(
            semaphore, "es", "en", LanguageLevel.A1, 
            "Greetings", ExerciseType.TRANSLATION, 10
        )
        
        assert result["success"] is False
        assert "error" in result
        assert result["generated_count"] == 0
    
    def test_create_seed_topics(self, generator, mock_session):
        """Test creating seed topics."""
        # Mock topic check
        generator.exercise_repo.get_by_field.return_value = None
        
        # Mock Topic creation
        with patch('src.orchestrator.curriculum_seed.Topic') as mock_topic_class:
            mock_topic = MagicMock()
            mock_topic_class.return_value = mock_topic
            
            topics = generator.create_seed_topics()
        
        assert len(topics) > 0
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    def test_create_seed_topics_existing(self, generator, mock_session):
        """Test creating seed topics when they already exist."""
        # Mock topic exists
        generator.exercise_repo.get_by_field.return_value = MagicMock()
        
        topics = generator.create_seed_topics()
        
        assert len(topics) == 0
        mock_session.add.assert_not_called()
    
    def test_generate_sample_users(self, generator):
        """Test generating sample users."""
        # Mock user creation
        generator.user_repo.get_or_create_user.return_value = (MagicMock(), True)
        
        users = generator.generate_sample_users(10)
        
        assert len(users) == 10
        assert generator.user_repo.get_or_create_user.call_count == 10
    
    @pytest.mark.asyncio
    async def test_generate_quick_seed(self, generator):
        """Test quick seed generation."""
        # Mock content generation
        generator.content_agent.generate_exercises = AsyncMock(return_value={
            "success": True,
            "generated_count": 25,
            "saved_count": 25
        })
        
        result = await generator.generate_quick_seed(exercises_per_language_pair=100)
        
        assert result["total_generations"] > 0
        assert result["successful_generations"] > 0
        assert result["total_exercises_generated"] > 0
        assert "language_pairs" in result
    
    @pytest.mark.asyncio
    async def test_generate_quick_seed_with_failures(self, generator):
        """Test quick seed generation with some failures."""
        # Mock content generation with mixed success/failure
        generator.content_agent.generate_exercises = AsyncMock(
            side_effect=[
                {"success": True, "generated_count": 25, "saved_count": 25},
                {"success": False, "error": "API error"},
                {"success": True, "generated_count": 25, "saved_count": 25}
            ]
        )
        
        result = await generator.generate_quick_seed(exercises_per_language_pair=100)
        
        assert result["total_generations"] > 0
        assert result["successful_generations"] > 0
        assert result["failed_generations"] > 0
        assert result["total_exercises_generated"] > 0
    
    def test_language_pairs_configuration(self, generator):
        """Test language pairs are properly configured."""
        expected_pairs = [
            ("es", "en"), ("en", "es"), ("fr", "en"), ("en", "fr"),
            ("de", "en"), ("en", "de"), ("pt", "en"), ("en", "pt"),
            ("it", "en"), ("en", "it")
        ]
        
        assert generator.language_pairs == expected_pairs
        assert len(generator.language_pairs) == 10
    
    def test_topics_by_level_configuration(self, generator):
        """Test topics are properly configured by level."""
        # Check A1 topics
        a1_topics = generator.topics_by_level[LanguageLevel.A1]
        assert "Greetings and Introductions" in a1_topics
        assert "Basic Numbers and Time" in a1_topics
        assert len(a1_topics) == 10
        
        # Check A2 topics
        a2_topics = generator.topics_by_level[LanguageLevel.A2]
        assert "Shopping and Commerce" in a2_topics
        assert "Travel and Directions" in a2_topics
        assert len(a2_topics) == 10
        
        # Check B1 topics
        b1_topics = generator.topics_by_level[LanguageLevel.B1]
        assert "Current Events and News" in b1_topics
        assert "Culture and Traditions" in b1_topics
        assert len(b1_topics) == 10
        
        # Check B2 topics
        b2_topics = generator.topics_by_level[LanguageLevel.B2]
        assert "Politics and Government" in b2_topics
        assert "Philosophy and Ethics" in b2_topics
        assert len(b2_topics) == 10
