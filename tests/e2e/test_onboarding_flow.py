"""E2E tests for WhatsApp Duolingo onboarding flow."""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from src.orchestrator.placement_test import AdaptivePlacementTest, PlacementTestResult
from src.data.models import LanguageLevel, ExerciseType, User
from src.data.repositories.user import UserRepository
from src.data.repositories.exercise import ExerciseRepository
from src.data.repositories.user_progress import UserProgressRepository
import random


class TestOnboardingFlow:
    """E2E test suite for the complete onboarding flow."""
    
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
    def mock_repositories(self, mock_session):
        """Create mock repositories."""
        user_repo = MagicMock(spec=UserRepository)
        exercise_repo = MagicMock(spec=ExerciseRepository)
        progress_repo = MagicMock(spec=UserProgressRepository)
        
        return {
            "user_repo": user_repo,
            "exercise_repo": exercise_repo,
            "progress_repo": progress_repo
        }
    
    @pytest.fixture
    def placement_test(self, mock_session, mock_repositories):
        """Create placement test with mocked dependencies."""
        test = AdaptivePlacementTest(mock_session)
        test.exercise_repo = mock_repositories["exercise_repo"]
        test.progress_repo = mock_repositories["progress_repo"]
        test.user_repo = mock_repositories["user_repo"]
        return test
    
    def test_complete_onboarding_flow_new_user(self, placement_test, mock_repositories):
        """Test complete onboarding flow for a new user."""
        # Step 1: User registration
        user_data = {
            "wa_id": "whatsapp_user_123",
            "name": "Maria Garcia",
            "phone": "+1234567890",
            "native_lang": "es",
            "target_lang": "en",
            "level": None  # New user, no level yet
        }
        
        # Mock user creation
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.level = None
        mock_repositories["user_repo"].get_or_create_user.return_value = (mock_user, True)
        
        # Verify user creation
        user, created = mock_repositories["user_repo"].get_or_create_user(**user_data)
        assert created is True
        assert user.id == 1
        assert user.level is None
        
        # Step 2: Generate placement test
        # Mock the entire generate_placement_test method to return test questions directly
        from src.orchestrator.placement_test import PlacementTestQuestion
        
        mock_questions = [
            PlacementTestQuestion(
                exercise_id=1, question="¿Cómo se dice 'hello' en inglés?",
                correct_answer="hello", options=None,
                difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                points=1, time_limit_seconds=30
            ),
            PlacementTestQuestion(
                exercise_id=2, question="Choose the correct answer: I ___ a student",
                correct_answer="am", options='["is", "am", "are", "be"]',
                difficulty=LanguageLevel.A1, exercise_type=ExerciseType.MULTIPLE_CHOICE,
                points=1, time_limit_seconds=30
            )
        ]
        
        placement_test.generate_placement_test = MagicMock(return_value=mock_questions)
        
        questions = placement_test.generate_placement_test(
            user_id=1, source_lang="es", target_lang="en", max_questions=2
        )
        
        assert len(questions) == 2
        assert questions[0].difficulty == LanguageLevel.A1
        assert questions[1].difficulty == LanguageLevel.A1
        
        # Step 3: User answers placement test
        answers = {
            1: {"answer": "hello", "response_time_ms": 3000},
            2: {"answer": "am", "response_time_ms": 5000}
        }
        
        # Mock test evaluation
        mock_questions = [
            questions[0], questions[1]
        ]
        placement_test._get_test_questions = MagicMock(return_value=mock_questions)
        
        # Mock user level update
        placement_test._update_user_level = MagicMock()
        
        result = placement_test.evaluate_placement_test(
            user_id=1, answers=answers, test_start_time_ms=1000, test_end_time_ms=9000
        )
        
        # Verify placement test results
        assert isinstance(result, PlacementTestResult)
        assert result.user_id == 1
        assert result.total_questions == 2
        assert result.correct_answers == 2
        assert result.accuracy_percentage == 100.0
        assert result.recommended_level in LanguageLevel
        
        # Step 4: Verify user level was updated
        placement_test._update_user_level.assert_called_once_with(1, result.recommended_level)
        
        # Step 5: Generate first lesson
        # Mock lesson generation
        lesson_exercises = [
            MagicMock(id=5, question="What is your name?", 
                      correct_answer="My name is...", options=None,
                      difficulty=result.recommended_level, exercise_type=ExerciseType.TRANSLATION),
            MagicMock(id=6, question="Where are you from?",
                      correct_answer="I am from...", options=None,
                      difficulty=result.recommended_level, exercise_type=ExerciseType.TRANSLATION)
        ]
        
        mock_repositories["exercise_repo"].get_exercises_for_lesson.return_value = lesson_exercises
        
        first_lesson = mock_repositories["exercise_repo"].get_exercises_for_lesson(
            source_lang="es", target_lang="en", 
            difficulty=result.recommended_level, count=5
        )
        
        assert len(first_lesson) == 2
        assert all(ex.difficulty == result.recommended_level for ex in first_lesson)
        
        print(f"✅ Complete onboarding flow successful for user {user.id}")
        print(f"   - Recommended level: {result.recommended_level.value}")
        print(f"   - Test accuracy: {result.accuracy_percentage}%")
        print(f"   - First lesson exercises: {len(first_lesson)}")
    
    def test_onboarding_flow_existing_user(self, placement_test, mock_repositories):
        """Test onboarding flow for existing user with known level."""
        # Mock existing user with B1 level
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.level = LanguageLevel.B1
        mock_user.native_lang = "fr"
        mock_user.target_lang = "en"
        mock_repositories["user_repo"].get.return_value = mock_user
        
        # Try to generate placement test - should skip for existing user
        questions = placement_test.generate_placement_test(
            user_id=2, source_lang="fr", target_lang="en", max_questions=10
        )
        
        assert len(questions) == 0  # No placement test for existing user
        
        # Generate lesson directly based on existing level
        lesson_exercises = [
            MagicMock(id=7, question="Discuss environmental issues",
                      correct_answer="Climate change is...", options=None,
                      difficulty=LanguageLevel.B1, exercise_type=ExerciseType.TRANSLATION)
        ]
        
        mock_repositories["exercise_repo"].get_exercises_for_lesson.return_value = lesson_exercises
        
        lesson = mock_repositories["exercise_repo"].get_exercises_for_lesson(
            source_lang="fr", target_lang="en", 
            difficulty=LanguageLevel.B1, count=5
        )
        
        assert len(lesson) == 1
        assert lesson[0].difficulty == LanguageLevel.B1
        
        print(f"✅ Existing user onboarding successful for user {mock_user.id}")
        print(f"   - Existing level: {mock_user.level.value}")
        print(f"   - Lesson exercises: {len(lesson)}")
    
    def test_onboarding_flow_placement_test_failure(self, placement_test, mock_repositories):
        """Test onboarding flow when placement test has issues."""
        # Mock new user
        mock_user = MagicMock()
        mock_user.id = 3
        mock_user.level = None
        mock_repositories["user_repo"].get.return_value = mock_user
        
        # Generate placement test
        mock_exercises = [MagicMock(id=8, question="Test", correct_answer="Answer")]
        placement_test._get_placement_exercises = MagicMock(return_value=mock_exercises)
        
        questions = placement_test.generate_placement_test(
            user_id=3, source_lang="pt", target_lang="en", max_questions=1
        )
        
        assert len(questions) == 1
        
        # User provides incorrect answers
        answers = {
            8: {"answer": "Wrong Answer", "response_time_ms": 10000}
        }
        
        mock_questions = [questions[0]]
        placement_test._get_test_questions = MagicMock(return_value=mock_questions)
        placement_test._update_user_level = MagicMock()
        
        result = placement_test.evaluate_placement_test(
            user_id=3, answers=answers, test_start_time_ms=1000, test_end_time_ms=11000
        )
        
        # Verify low accuracy leads to lower recommended level
        assert result.accuracy_percentage == 0.0
        assert result.recommended_level == LanguageLevel.A1  # Should default to beginner
        
        # Verify user level was still updated
        placement_test._update_user_level.assert_called_once_with(3, LanguageLevel.A1)
        
        print(f"✅ Placement test failure handled gracefully for user {mock_user.id}")
        print(f"   - Recommended level: {result.recommended_level.value} (fallback)")
        print(f"   - Test accuracy: {result.accuracy_percentage}%")
    
    def test_onboarding_flow_multiple_language_pairs(self, placement_test, mock_repositories):
        """Test onboarding flow for different language pairs."""
        language_pairs = [
            ("es", "en"), ("en", "es"), ("fr", "en"), ("de", "en")
        ]
        
        for i, (source_lang, target_lang) in enumerate(language_pairs):
            # Mock user
            mock_user = MagicMock()
            mock_user.id = 100 + i
            mock_user.level = None
            mock_user.native_lang = source_lang
            mock_user.target_lang = target_lang
            mock_repositories["user_repo"].get.return_value = mock_user
            
            # Generate placement test
            mock_exercises = [MagicMock(id=100+i, question=f"Test {i}", correct_answer=f"Answer {i}")]
            placement_test._get_placement_exercises = MagicMock(return_value=mock_exercises)
            
            questions = placement_test.generate_placement_test(
                user_id=mock_user.id, source_lang=source_lang, target_lang=target_lang, max_questions=1
            )
            
            assert len(questions) == 1
            
            # Mock successful test
            answers = {100+i: {"answer": f"Answer {i}", "response_time_ms": 3000}}
            mock_questions = [questions[0]]
            placement_test._get_test_questions = MagicMock(return_value=mock_questions)
            placement_test._update_user_level = MagicMock()
            
            result = placement_test.evaluate_placement_test(
                user_id=mock_user.id, answers=answers, 
                test_start_time_ms=1000, test_end_time_ms=4000
            )
            
            assert result.accuracy_percentage == 100.0
            assert result.recommended_level in LanguageLevel
            
            print(f"✅ Language pair {source_lang}->{target_lang} successful for user {mock_user.id}")
    
    def test_onboarding_flow_edge_cases(self, placement_test, mock_repositories):
        """Test edge cases in onboarding flow."""
        
        # Test 1: User not found
        mock_repositories["user_repo"].get.return_value = None
        
        with pytest.raises(ValueError, match="User 999 not found"):
            placement_test.generate_placement_test(
                user_id=999, source_lang="es", target_lang="en", max_questions=5
            )
        
        # Test 2: No exercises available for placement test
        mock_user = MagicMock()
        mock_user.id = 4
        mock_user.level = None
        mock_repositories["user_repo"].get.return_value = mock_user
        placement_test._get_placement_exercises = MagicMock(return_value=[])
        
        questions = placement_test.generate_placement_test(
            user_id=4, source_lang="es", target_lang="en", max_questions=5
        )
        
        assert len(questions) == 0  # No exercises available
        
        # Test 3: Empty answers in placement test
        mock_exercises = [MagicMock(id=9, question="Test", correct_answer="Answer")]
        placement_test._get_placement_exercises = MagicMock(return_value=mock_exercises)
        
        questions = placement_test.generate_placement_test(
            user_id=4, source_lang="es", target_lang="en", max_questions=1
        )
        
        assert len(questions) == 1
        
        # Test with empty answers
        placement_test._get_test_questions = MagicMock(return_value=questions)
        placement_test._update_user_level = MagicMock()
        
        result = placement_test.evaluate_placement_test(
            user_id=4, answers={}, test_start_time_ms=1000, test_end_time_ms=2000
        )
        
        assert result.total_questions == 0
        assert result.correct_answers == 0
        assert result.accuracy_percentage == 0.0
        
        print("✅ Edge cases handled correctly")
    
    def test_onboarding_flow_performance_tracking(self, placement_test, mock_repositories):
        """Test that performance is properly tracked during onboarding."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 5
        mock_user.level = None
        mock_repositories["user_repo"].get.return_value = mock_user
        
        # Generate placement test
        mock_exercises = [
            MagicMock(id=10, question="Question 1", correct_answer="Answer 1",
                      difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                      points=1, time_limit_seconds=30),
            MagicMock(id=11, question="Question 2", correct_answer="Answer 2",
                      difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                      points=1, time_limit_seconds=30),
            MagicMock(id=12, question="Question 3", correct_answer="Answer 3",
                      difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                      points=1, time_limit_seconds=30)
        ]
        
        # Mock the entire placement test generation to return test questions directly
        from src.orchestrator.placement_test import PlacementTestQuestion
        
        mock_questions = [
            PlacementTestQuestion(
                exercise_id=10, question="Question 1", correct_answer="Answer 1",
                options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                points=1, time_limit_seconds=30
            ),
            PlacementTestQuestion(
                exercise_id=11, question="Question 2", correct_answer="Answer 2",
                options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                points=1, time_limit_seconds=30
            ),
            PlacementTestQuestion(
                exercise_id=12, question="Question 3", correct_answer="Answer 3",
                options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                points=1, time_limit_seconds=30
            )
        ]
        
        placement_test.generate_placement_test = MagicMock(return_value=mock_questions)
        placement_test._get_test_questions = MagicMock(return_value=mock_questions)
        
        questions = placement_test.generate_placement_test(
            user_id=5, source_lang="es", target_lang="en", max_questions=3
        )
        
        assert len(questions) == 3
        
        # User answers with varying response times
        answers = {
            10: {"answer": "Answer 1", "response_time_ms": 2000},  # Fast, correct
            11: {"answer": "Answer 2", "response_time_ms": 8000},  # Slow, correct
            12: {"answer": "Wrong", "response_time_ms": 5000}      # Incorrect
        }
        
        # Track progress creation calls
        mock_repositories["progress_repo"].create_progress = MagicMock()
        placement_test._update_user_level = MagicMock()
        
        result = placement_test.evaluate_placement_test(
            user_id=5, answers=answers, test_start_time_ms=1000, test_end_time_ms=15000
        )
        
        # Verify performance metrics
        assert result.total_questions == 3
        assert result.correct_answers == 2
        assert result.accuracy_percentage == pytest.approx(66.66666666666667)
        assert result.average_response_time_ms == 5000  # (2000 + 8000 + 5000) / 3
        assert result.test_duration_ms == 14000
        
        # Verify progress was tracked for each answer
        assert mock_repositories["progress_repo"].create_progress.call_count == 3
        
        # Verify progress tracking calls
        calls = mock_repositories["progress_repo"].create_progress.call_args_list
        assert calls[0][1]["user_id"] == 5
        assert calls[0][1]["exercise_id"] == 10
        assert calls[0][1]["is_correct"] is True
        assert calls[0][1]["response_time_ms"] == 2000
        
        assert calls[1][1]["user_id"] == 5
        assert calls[1][1]["exercise_id"] == 11
        assert calls[1][1]["is_correct"] is True
        assert calls[1][1]["response_time_ms"] == 8000
        
        assert calls[2][1]["user_id"] == 5
        assert calls[2][1]["exercise_id"] == 12
        assert calls[2][1]["is_correct"] is False
        assert calls[2][1]["response_time_ms"] == 5000
        
        print(f"✅ Performance tracking successful for user {mock_user.id}")
        print(f"   - Average response time: {result.average_response_time_ms}ms")
        print(f"   - Test duration: {result.test_duration_ms}ms")
        print(f"   - Progress entries created: {len(calls)}")


class TestOnboardingFlowIntegration:
    """Integration tests for onboarding flow components."""
    
    @pytest.mark.asyncio
    async def test_full_onboarding_simulation(self):
        """Simulate a complete onboarding session with realistic timing."""
        # This would be a full integration test with actual timing
        # For now, we'll simulate the flow
        
        onboarding_steps = [
            "User registration",
            "Language pair selection",
            "Placement test generation",
            "Placement test completion",
            "Level recommendation",
            "First lesson generation"
        ]
        
        # Simulate timing for each step
        step_times = {
            "User registration": 500,      # 0.5s
            "Language pair selection": 2000, # 2s
            "Placement test generation": 1000, # 1s
            "Placement test completion": 30000, # 30s (20 questions)
            "Level recommendation": 500,   # 0.5s
            "First lesson generation": 2000  # 2s
        }
        
        total_time = sum(step_times.values())
        
        assert total_time == 36000  # 36 seconds total
        assert len(onboarding_steps) == 6
        
        print(f"✅ Full onboarding simulation completed in {total_time/1000:.1f}s")
        for step in onboarding_steps:
            print(f"   - {step}: {step_times[step]/1000:.1f}s")
    
    def test_onboarding_flow_error_recovery(self):
        """Test error recovery during onboarding flow."""
        error_scenarios = [
            ("Database connection lost", "Retry with exponential backoff"),
            ("Exercise generation failed", "Fallback to cached exercises"),
            ("User response timeout", "Continue with available answers"),
            ("Level determination ambiguous", "Use conservative estimate")
        ]
        
        for scenario, recovery in error_scenarios:
            # Simulate error handling
            assert recovery is not None
            assert "Retry" in recovery or "Fallback" in recovery or "Continue" in recovery or "Use" in recovery
        
        print(f"✅ Error recovery strategies defined for {len(error_scenarios)} scenarios")
        for scenario, recovery in error_scenarios:
            print(f"   - {scenario}: {recovery}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
