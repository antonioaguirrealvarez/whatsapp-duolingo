"""Unit tests for Adaptive Placement Test."""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from src.orchestrator.placement_test import (
    AdaptivePlacementTest,
    PlacementTestQuestion,
    PlacementTestResult
)
from src.data.models import LanguageLevel, ExerciseType, User, Exercise


class TestAdaptivePlacementTest:
    """Test suite for AdaptivePlacementTest."""
    
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
    def placement_test(self, mock_session):
        """Create adaptive placement test with mocked dependencies."""
        # Create mock repositories
        mock_exercise_repo = MagicMock()
        mock_progress_repo = MagicMock()
        mock_user_repo = MagicMock()
        
        # Create placement test with mocked session
        test = AdaptivePlacementTest(mock_session)
        
        # Replace repositories with mocks
        test.exercise_repo = mock_exercise_repo
        test.progress_repo = mock_progress_repo
        test.user_repo = mock_user_repo
        
        return test
    
    def test_initialization(self, placement_test):
        """Test placement test initialization."""
        assert placement_test.difficulty_order == [
            LanguageLevel.A1, LanguageLevel.A2, LanguageLevel.B1, LanguageLevel.B2
        ]
        assert placement_test.points_by_difficulty[LanguageLevel.A1] == 1
        assert placement_test.points_by_difficulty[LanguageLevel.B2] == 4
        assert placement_test.time_limits[LanguageLevel.A1] == 30
        assert placement_test.time_limits[LanguageLevel.B2] == 90
    
    def test_generate_placement_test_new_user(self, placement_test):
        """Test generating placement test for new user."""
        # Mock user
        mock_user = MagicMock()
        mock_user.level = None
        placement_test.user_repo.get.return_value = mock_user
        
        # Mock exercises
        mock_exercises = [
            MagicMock(id=1, question="Test 1", correct_answer="Answer 1", 
                      options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION),
            MagicMock(id=2, question="Test 2", correct_answer="Answer 2",
                      options='["A", "B", "C", "D"]', difficulty=LanguageLevel.A1, exercise_type=ExerciseType.MULTIPLE_CHOICE)
        ]
        placement_test._get_placement_exercises = MagicMock(return_value=mock_exercises)
        
        with patch('src.orchestrator.placement_test.random.choice', side_effect=[mock_exercises[0], mock_exercises[1]]):
            questions = placement_test.generate_placement_test(
                user_id=1, source_lang="es", target_lang="en", max_questions=2
            )
        
        assert len(questions) == 2
        assert questions[0].exercise_id == 1
        assert questions[0].difficulty == LanguageLevel.A1
        assert questions[0].points == 1
        assert questions[0].time_limit_seconds == 30
        
        assert questions[1].exercise_id == 2
        assert questions[1].exercise_type == ExerciseType.MULTIPLE_CHOICE
    
    def test_generate_placement_test_user_with_level(self, placement_test):
        """Test generating placement test for user who already has a level."""
        # Mock user with existing level
        mock_user = MagicMock()
        mock_user.level = LanguageLevel.B1
        placement_test.user_repo.get.return_value = mock_user
        
        questions = placement_test.generate_placement_test(
            user_id=1, source_lang="es", target_lang="en", max_questions=10
        )
        
        assert len(questions) == 0
    
    def test_generate_placement_test_user_not_found(self, placement_test):
        """Test generating placement test for non-existent user."""
        placement_test.user_repo.get.return_value = None
        
        with pytest.raises(ValueError, match="User 1 not found"):
            placement_test.generate_placement_test(
                user_id=1, source_lang="es", target_lang="en", max_questions=10
            )
    
    def test_get_placement_exercises(self, placement_test):
        """Test getting placement exercises."""
        mock_exercises = [MagicMock(), MagicMock()]
        placement_test.exercise_repo.get_exercises_for_lesson.return_value = mock_exercises
        
        result = placement_test._get_placement_exercises(
            "es", "en", LanguageLevel.A1, count=5
        )
        
        assert result == mock_exercises
        placement_test.exercise_repo.get_exercises_for_lesson.assert_called_once_with(
            source_lang="es", target_lang="en", difficulty=LanguageLevel.A1,
            count=10, exercise_types=[ExerciseType.TRANSLATION, ExerciseType.MULTIPLE_CHOICE]
        )
    
    def test_evaluate_placement_test(self, placement_test):
        """Test evaluating placement test answers."""
        # Mock questions
        mock_questions = [
            PlacementTestQuestion(
                exercise_id=1, question="Test 1", correct_answer="hello",
                options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                points=1, time_limit_seconds=30
            ),
            PlacementTestQuestion(
                exercise_id=2, question="Test 2", correct_answer="world",
                options=None, difficulty=LanguageLevel.A2, exercise_type=ExerciseType.TRANSLATION,
                points=2, time_limit_seconds=45
            )
        ]
        placement_test._get_test_questions = MagicMock(return_value=mock_questions)
        
        # Mock progress creation
        placement_test.progress_repo.create_progress.return_value = MagicMock()
        
        # Mock user update
        placement_test._update_user_level = MagicMock()
        
        answers = {
            1: {"answer": "hello", "response_time_ms": 5000},
            2: {"answer": "world", "response_time_ms": 8000}
        }
        
        result = placement_test.evaluate_placement_test(
            user_id=1, answers=answers, test_start_time_ms=1000, test_end_time_ms=20000
        )
        
        assert isinstance(result, PlacementTestResult)
        assert result.user_id == 1
        assert result.total_questions == 2
        assert result.correct_answers == 2
        assert result.accuracy_percentage == 100.0
        assert result.average_response_time_ms == 6500
        assert result.test_duration_ms == 19000
        assert result.recommended_level in LanguageLevel
        assert 0 <= result.confidence_score <= 1.0
    
    def test_evaluate_answer_exact_match(self, placement_test):
        """Test answer evaluation with exact match."""
        question = PlacementTestQuestion(
            exercise_id=1, question="Test", correct_answer="Hello",
            options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
            points=1, time_limit_seconds=30
        )
        
        assert placement_test._evaluate_answer(question, "Hello") is True
        assert placement_test._evaluate_answer(question, "hello") is True
        assert placement_test._evaluate_answer(question, "HELLO") is True
        assert placement_test._evaluate_answer(question, "hello ") is True
        assert placement_test._evaluate_answer(question, " hello") is True
        assert placement_test._evaluate_answer(question, "goodbye") is False
    
    def test_evaluate_answer_multiple_choice(self, placement_test):
        """Test answer evaluation for multiple choice."""
        question = PlacementTestQuestion(
            exercise_id=1, question="Test", correct_answer="B",
            options='["A", "B", "C", "D"]', difficulty=LanguageLevel.A1,
            exercise_type=ExerciseType.MULTIPLE_CHOICE, points=1, time_limit_seconds=30
        )
        
        assert placement_test._evaluate_answer(question, "B") is True
        assert placement_test._evaluate_answer(question, "b") is True
        assert placement_test._evaluate_answer(question, "A") is False
    
    def test_fuzzy_match(self, placement_test):
        """Test fuzzy matching for translations."""
        # Exact matches
        assert placement_test._fuzzy_match("hello", "hello") is True
        assert placement_test._fuzzy_match("hello world", "hello world") is True
        
        # With punctuation
        assert placement_test._fuzzy_match("hello, world!", "hello world") is True
        assert placement_test._fuzzy_match("how are you?", "how are you") is True
        
        # Word overlap
        assert placement_test._fuzzy_match("hello my friend", "hello friend") is False  # 2/3 overlap = 67% < 80%
        assert placement_test._fuzzy_match("hello friend", "hello friend") is True  # 2/2 overlap = 100% >= 80%
        assert placement_test._fuzzy_match("good morning", "good night") is False
        
        # Different words
        assert placement_test._fuzzy_match("completely different", "not at all similar") is False
    
    def test_determine_level_perfect_score(self, placement_test):
        """Test level determination with perfect scores."""
        difficulty_performance = {
            LanguageLevel.A1: {"correct": 5, "total": 5},
            LanguageLevel.A2: {"correct": 5, "total": 5},
            LanguageLevel.B1: {"correct": 5, "total": 5},
            LanguageLevel.B2: {"correct": 5, "total": 5}
        }
        
        level, confidence = placement_test._determine_level(difficulty_performance, 100)
        
        # Should recommend highest level with high confidence
        assert level == LanguageLevel.B2
        assert confidence >= 0.8
    
    def test_determine_level_mixed_performance(self, placement_test):
        """Test level determination with mixed performance."""
        difficulty_performance = {
            LanguageLevel.A1: {"correct": 5, "total": 5},  # 100%
            LanguageLevel.A2: {"correct": 3, "total": 5},  # 60%
            LanguageLevel.B1: {"correct": 2, "total": 5},  # 40%
            LanguageLevel.B2: {"correct": 1, "total": 5}   # 20%
        }
        
        level, confidence = placement_test._determine_level(difficulty_performance, 60)
        
        # Should recommend A1 or A2 based on scoring
        assert level in [LanguageLevel.A1, LanguageLevel.A2]
        assert 0 <= confidence <= 1.0
    
    def test_analyze_areas(self, placement_test):
        """Test analyzing weak and strong areas."""
        difficulty_performance = {
            LanguageLevel.A1: {"correct": 5, "total": 5},  # 100% - strong
            LanguageLevel.A2: {"correct": 4, "total": 5},  # 80% - strong
            LanguageLevel.B1: {"correct": 2, "total": 5},  # 40% - weak
            LanguageLevel.B2: {"correct": 1, "total": 5}   # 20% - weak
        }
        
        weak_areas, strong_areas = placement_test._analyze_areas(difficulty_performance)
        
        assert "B1 level" in weak_areas
        assert "B2 level" in weak_areas
        assert "A1 level" in strong_areas
        assert "A2 level" in strong_areas
    
    def test_update_user_level(self, placement_test):
        """Test updating user level."""
        mock_user = MagicMock()
        placement_test.user_repo.get.return_value = mock_user
        
        placement_test._update_user_level(1, LanguageLevel.B1)
        
        assert mock_user.level == LanguageLevel.B1
        placement_test.db_session.commit.assert_called_once()
    
    def test_get_test_questions(self, placement_test):
        """Test getting test questions from exercise IDs."""
        mock_exercise = MagicMock(
            id=1, question="Test", correct_answer="Answer",
            options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION
        )
        placement_test.exercise_repo.get.return_value = mock_exercise
        
        questions = placement_test._get_test_questions(1, [1])
        
        assert len(questions) == 1
        assert questions[0].exercise_id == 1
        assert questions[0].question == "Test"
        assert questions[0].points == 1
        assert questions[0].time_limit_seconds == 30
    
    def test_get_placement_test_history(self, placement_test):
        """Test getting placement test history."""
        # Mock recent progress
        mock_progress = [
            MagicMock(is_correct=True, created_at=MagicMock()),
            MagicMock(is_correct=False, created_at=MagicMock()),
            MagicMock(is_correct=True, created_at=MagicMock())
        ]
        placement_test.progress_repo.get_user_recent_progress.return_value = mock_progress
        
        history = placement_test.get_placement_test_history(1)
        
        assert len(history) == 1
        assert history[0]["total_questions"] == 3
        assert history[0]["correct_answers"] == 2
        assert history[0]["accuracy"] == pytest.approx(66.66666666666667)
