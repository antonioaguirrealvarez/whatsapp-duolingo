"""Unit tests for repository pattern."""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from src.data.models import User, Exercise, UserProgress, LanguageLevel, ExerciseType, ErrorType
from src.data.repositories.base import BaseRepository
from src.data.repositories.user import UserRepository
from src.data.repositories.exercise import ExerciseRepository
from src.data.repositories.user_progress import UserProgressRepository


class TestBaseRepository:
    """Test suite for BaseRepository."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=Session)
        session.query.return_value = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        session.delete.return_value = None
        return session
    
    @pytest.fixture
    def base_repo(self, mock_session):
        """Create base repository instance."""
        return BaseRepository(User, mock_session)
    
    def test_create(self, base_repo, mock_session):
        """Test creating a record."""
        user_data = {"wa_id": "123", "name": "Test User"}
        mock_user = User(**user_data)
        mock_session.add.return_value = None
        mock_session.refresh.return_value = None
        
        with patch.object(base_repo.model, '__init__', return_value=None):
            result = base_repo.create(user_data)
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    def test_get(self, base_repo, mock_session):
        """Test getting a record by ID."""
        mock_user = User(id=1, wa_id="123")
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = base_repo.get(1)
        
        assert result == mock_user
        mock_session.query.assert_called_once_with(User)
    
    def test_get_by_field(self, base_repo, mock_session):
        """Test getting a record by field value."""
        mock_user = User(wa_id="123")
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = base_repo.get_by_field("wa_id", "123")
        
        assert result == mock_user
    
    def test_get_by_field_invalid_field(self, base_repo):
        """Test getting by invalid field raises error."""
        with pytest.raises(ValueError, match="has no field 'invalid'"):
            base_repo.get_by_field("invalid", "value")
    
    def test_update(self, base_repo, mock_session):
        """Test updating a record."""
        mock_user = User(id=1, wa_id="123")
        update_data = {"name": "Updated Name"}
        
        result = base_repo.update(mock_user, update_data)
        
        mock_session.add.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_user)


class TestUserRepository:
    """Test suite for UserRepository."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=Session)
        session.query.return_value = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session
    
    @pytest.fixture
    def user_repo(self, mock_session):
        """Create user repository instance."""
        return UserRepository(mock_session)
    
    def test_get_by_wa_id(self, user_repo, mock_session):
        """Test getting user by WhatsApp ID."""
        mock_user = User(wa_id="1234567890")
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = user_repo.get_by_wa_id("1234567890")
        
        assert result == mock_user
    
    def test_create_user(self, user_repo, mock_session):
        """Test creating a new user."""
        user_data = {
            "wa_id": "123",
            "name": "Test User",
            "native_lang": "es",
            "target_lang": "en",
            "level": LanguageLevel.A1
        }
        
        with patch.object(user_repo, 'create') as mock_create:
            mock_create.return_value = User(**user_data)
            result = user_repo.create_user(**user_data)
        
        assert result.wa_id == "123"
        mock_create.assert_called_once()
    
    def test_get_or_create_user_existing(self, user_repo, mock_session):
        """Test getting or creating user when user exists."""
        mock_user = User(wa_id="123")
        
        with patch.object(user_repo, 'get_by_wa_id', return_value=mock_user):
            result, created = user_repo.get_or_create_user("123")
        
        assert result == mock_user
        assert created is False
    
    def test_get_or_create_user_new(self, user_repo, mock_session):
        """Test getting or creating user when user doesn't exist."""
        with patch.object(user_repo, 'get_by_wa_id', return_value=None), \
             patch.object(user_repo, 'create_user') as mock_create:
            mock_create.return_value = User(wa_id="123")
            result, created = user_repo.get_or_create_user("123")
        
        assert result.wa_id == "123"
        assert created is True
        mock_create.assert_called_once_with(wa_id="123")


class TestExerciseRepository:
    """Test suite for ExerciseRepository."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=Session)
        session.query.return_value = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session
    
    @pytest.fixture
    def exercise_repo(self, mock_session):
        """Create exercise repository instance."""
        return ExerciseRepository(mock_session)
    
    def test_get_by_language_pair(self, exercise_repo, mock_session):
        """Test getting exercises by language pair."""
        mock_exercises = [Exercise(id=1), Exercise(id=2)]
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_exercises
        
        result = exercise_repo.get_by_language_pair("es", "en")
        
        assert result == mock_exercises
        mock_query.filter.assert_called()
    
    def test_create_exercise(self, exercise_repo, mock_session):
        """Test creating a new exercise."""
        exercise_data = {
            "question": "Test question",
            "correct_answer": "Test answer",
            "difficulty": LanguageLevel.A1,
            "exercise_type": ExerciseType.TRANSLATION,
            "source_lang": "es",
            "target_lang": "en"
        }
        
        with patch.object(exercise_repo, 'create') as mock_create:
            mock_create.return_value = Exercise(**exercise_data)
            result = exercise_repo.create_exercise(**exercise_data)
        
        assert result.question == "Test question"
        mock_create.assert_called_once()
    
    def test_search_exercises(self, exercise_repo, mock_session):
        """Test searching exercises."""
        # Create a proper mock for the query chain
        mock_query_chain = MagicMock()
        mock_query_chain.all.return_value = [Exercise(id=1)]
        mock_session.query.return_value = mock_query_chain
        
        # Mock the contains method
        with patch('src.data.repositories.exercise.Exercise.question') as mock_question:
            mock_question.contains.return_value = True
            result = exercise_repo.search_exercises("hello")
        
        # Verify the result is not None
        assert result is not None
        mock_session.query.assert_called()


class TestUserProgressRepository:
    """Test suite for UserProgressRepository."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=Session)
        session.query.return_value = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session
    
    @pytest.fixture
    def progress_repo(self, mock_session):
        """Create user progress repository instance."""
        return UserProgressRepository(mock_session)
    
    def test_get_user_progress(self, progress_repo, mock_session):
        """Test getting user's progress for an exercise."""
        mock_progress = UserProgress(user_id=1, exercise_id=1)
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_progress
        
        result = progress_repo.get_user_progress(1, 1)
        
        assert result == mock_progress
    
    def test_create_progress(self, progress_repo, mock_session):
        """Test creating user progress."""
        progress_data = {
            "user_id": 1,
            "exercise_id": 1,
            "is_correct": True,
            "user_answer": "Test answer"
        }
        
        with patch.object(progress_repo, 'create') as mock_create:
            mock_create.return_value = UserProgress(**progress_data)
            result = progress_repo.create_progress(**progress_data)
        
        assert result.is_correct is True
        mock_create.assert_called_once()
    
    def test_get_user_accuracy_stats(self, progress_repo, mock_session):
        """Test getting user accuracy statistics."""
        # Mock total count
        with patch.object(progress_repo, 'count_by_field', return_value=10), \
             patch.object(progress_repo, 'get_user_correct_answers', return_value=[UserProgress() for _ in range(8)]), \
             patch.object(mock_session.query, 'return_value') as mock_query:
            
            # Mock error stats query
            mock_error_query = MagicMock()
            mock_error_query.filter.return_value.group_by.return_value.all.return_value = [
                (ErrorType.SPELLING, 2)
            ]
            mock_query.return_value = mock_error_query
            
            # Mock avg response time query
            mock_avg_query = MagicMock()
            mock_avg_query.filter.return_value.scalar.return_value = 5000
            mock_query.return_value = mock_avg_query
            
            result = progress_repo.get_user_accuracy_stats(1)
        
        assert result["total_exercises"] == 10
        assert result["correct_answers"] == 8
        assert result["accuracy_percentage"] == 80.0
    
    def test_get_or_create_progress_existing(self, progress_repo, mock_session):
        """Test getting or creating progress when it exists."""
        mock_progress = UserProgress(user_id=1, exercise_id=1)
        
        with patch.object(progress_repo, 'get_user_progress', return_value=mock_progress), \
             patch.object(progress_repo, 'update_progress') as mock_update:
            mock_update.return_value = mock_progress
            result, created = progress_repo.get_or_create_progress(
                1, 1, True, "answer"
            )
        
        assert result == mock_progress
        assert created is False
        mock_update.assert_called_once()
    
    def test_get_or_create_progress_new(self, progress_repo, mock_session):
        """Test getting or creating progress when it doesn't exist."""
        with patch.object(progress_repo, 'get_user_progress', return_value=None), \
             patch.object(progress_repo, 'create_progress') as mock_create:
            mock_create.return_value = UserProgress(user_id=1, exercise_id=1)
            result, created = progress_repo.get_or_create_progress(
                1, 1, True, "answer"
            )
        
        assert created is True
        mock_create.assert_called_once()
