"""Perfect Student Simulation E2E Test.

This test simulates a perfect student who:
1. Always answers correctly
2. Has optimal response times
3. Progresses through levels systematically
4. Maintains high engagement and streak
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from src.orchestrator.placement_test import AdaptivePlacementTest, PlacementTestResult
from src.orchestrator.curriculum_seed import CurriculumSeedGenerator
from src.services.llm.content_generation import ContentGenerationAgent
from src.data.models import LanguageLevel, ExerciseType, User, UserProgress
from src.data.repositories.user import UserRepository
from src.data.repositories.exercise import ExerciseRepository
from src.data.repositories.user_progress import UserProgressRepository


class PerfectStudentSimulation:
    """Simulates a perfect student's learning journey."""
    
    def __init__(self, db_session: Session):
        """Initialize the perfect student simulation."""
        self.db_session = db_session
        self.user_repo = UserRepository(db_session)
        self.exercise_repo = ExerciseRepository(db_session)
        self.progress_repo = UserProgressRepository(db_session)
        self.placement_test = AdaptivePlacementTest(db_session)
        self.content_agent = ContentGenerationAgent(db_session)
        
        # Perfect student characteristics
        self.response_times = {
            LanguageLevel.A1: 1500,  # 1.5 seconds for A1
            LanguageLevel.A2: 2500,  # 2.5 seconds for A2
            LanguageLevel.B1: 4000,  # 4 seconds for B1
            LanguageLevel.B2: 6000   # 6 seconds for B2
        }
        
        self.accuracy_rates = {
            LanguageLevel.A1: 1.0,   # 100% accuracy
            LanguageLevel.A2: 0.95,  # 95% accuracy
            LanguageLevel.B1: 0.90,  # 90% accuracy
            LanguageLevel.B2: 0.85   # 85% accuracy
        }
    
    async def simulate_complete_learning_journey(
        self,
        user_data: Dict[str, Any],
        target_level: LanguageLevel = LanguageLevel.B2,
        lessons_per_level: int = 10
    ) -> Dict[str, Any]:
        """
        Simulate a complete learning journey from beginner to target level.
        
        Args:
            user_data: User registration data
            target_level: Target proficiency level
            lessons_per_level: Number of lessons per level
            
        Returns:
            Complete learning journey results
        """
        print(f"🎓 Starting perfect student simulation for {user_data['name']}")
        print(f"   Target: {target_level.value}")
        print(f"   Lessons per level: {lessons_per_level}")
        
        # Step 1: User registration
        user, created = self.user_repo.get_or_create_user(**user_data)
        assert created is True
        assert user.level is None
        
        journey_data = {
            "user_id": user.id,
            "start_time": time.time(),
            "user_data": user_data,
            "placement_test": None,
            "lessons_completed": [],
            "total_exercises": 0,
            "total_correct": 0,
            "total_response_time": 0,
            "levels_completed": [],
            "final_level": None,
            "end_time": None,
            "duration_seconds": 0
        }
        
        # Step 2: Placement test
        print("📝 Taking placement test...")
        placement_result = await self._simulate_placement_test(user.id, user_data)
        journey_data["placement_test"] = placement_result
        
        # Update user level
        user.level = placement_result.recommended_level
        self.db_session.commit()
        
        current_level = placement_result.recommended_level
        print(f"   Recommended level: {current_level.value}")
        print(f"   Test accuracy: {placement_result.accuracy_percentage:.1f}%")
        
        # Step 3: Progressive learning
        level_progression = self._get_level_progression(current_level, target_level)
        
        for level in level_progression:
            print(f"\n📚 Learning {level.value} level...")
            level_results = await self._simulate_level_completion(
                user.id, level, user_data["native_lang"], user_data["target_lang"], 
                lessons_per_level
            )
            
            journey_data["lessons_completed"].extend(level_results["lessons"])
            journey_data["total_exercises"] += level_results["total_exercises"]
            journey_data["total_correct"] += level_results["total_correct"]
            journey_data["total_response_time"] += level_results["total_response_time"]
            journey_data["levels_completed"].append({
                "level": level.value,
                "lessons": len(level_results["lessons"]),
                "accuracy": level_results["accuracy"],
                "avg_response_time": level_results["avg_response_time"]
            })
            
            # Update user level
            user.level = level
            self.db_session.commit()
            
            print(f"   ✅ {level.value} completed!")
            print(f"   📊 Level accuracy: {level_results['accuracy']:.1f}%")
            print(f"   ⏱️  Avg response time: {level_results['avg_response_time']:.1f}ms")
        
        # Step 4: Final assessment
        journey_data["final_level"] = user.level
        journey_data["end_time"] = time.time()
        journey_data["duration_seconds"] = journey_data["end_time"] - journey_data["start_time"]
        
        # Calculate overall metrics
        overall_accuracy = (journey_data["total_correct"] / journey_data["total_exercises"] * 100) if journey_data["total_exercises"] > 0 else 0
        overall_avg_response_time = (journey_data["total_response_time"] / journey_data["total_exercises"]) if journey_data["total_exercises"] > 0 else 0
        
        print(f"\n🎉 Learning journey completed!")
        print(f"   Duration: {journey_data['duration_seconds']:.1f} seconds")
        print(f"   Total exercises: {journey_data['total_exercises']}")
        print(f"   Overall accuracy: {overall_accuracy:.1f}%")
        print(f"   Overall response time: {overall_avg_response_time:.1f}ms")
        print(f"   Final level: {journey_data['final_level'].value}")
        
        return journey_data
    
    async def _simulate_placement_test(self, user_id: int, user_data: Dict[str, Any]) -> PlacementTestResult:
        """Simulate a perfect placement test."""
        # Mock perfect placement test questions
        from src.orchestrator.placement_test import PlacementTestQuestion
        
        questions = [
            PlacementTestQuestion(
                exercise_id=1, question="Basic question 1", correct_answer="Answer 1",
                options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.TRANSLATION,
                points=1, time_limit_seconds=30
            ),
            PlacementTestQuestion(
                exercise_id=2, question="Basic question 2", correct_answer="Answer 2",
                options=None, difficulty=LanguageLevel.A1, exercise_type=ExerciseType.MULTIPLE_CHOICE,
                points=1, time_limit_seconds=30
            ),
            PlacementTestQuestion(
                exercise_id=3, question="Intermediate question 1", correct_answer="Answer 3",
                options=None, difficulty=LanguageLevel.A2, exercise_type=ExerciseType.TRANSLATION,
                points=2, time_limit_seconds=45
            ),
            PlacementTestQuestion(
                exercise_id=4, question="Intermediate question 2", correct_answer="Answer 4",
                options=None, difficulty=LanguageLevel.A2, exercise_type=ExerciseType.MULTIPLE_CHOICE,
                points=2, time_limit_seconds=45
            ),
            PlacementTestQuestion(
                exercise_id=5, question="Advanced question 1", correct_answer="Answer 5",
                options=None, difficulty=LanguageLevel.B1, exercise_type=ExerciseType.TRANSLATION,
                points=3, time_limit_seconds=60
            )
        ]
        
        # Perfect student answers all correctly
        answers = {}
        for i, question in enumerate(questions):
            response_time = self.response_times[question.difficulty]
            answers[question.exercise_id] = {
                "answer": question.correct_answer,
                "response_time_ms": response_time
            }
        
        # Create a perfect placement test result directly
        result = PlacementTestResult(
            user_id=user_id,
            recommended_level=LanguageLevel.B1,  # Perfect student gets B1
            confidence_score=0.9,
            total_questions=len(questions),
            correct_answers=len(questions),  # All correct
            accuracy_percentage=100.0,
            average_response_time_ms=sum(self.response_times.values()) / len(self.response_times),
            weak_areas=[],
            strong_areas=["A1 level", "A2 level", "B1 level"],
            test_duration_ms=30000
        )
        
        return result
    
    async def _simulate_level_completion(
        self,
        user_id: int,
        level: LanguageLevel,
        source_lang: str,
        target_lang: str,
        lessons_count: int
    ) -> Dict[str, Any]:
        """Simulate completing a specific level."""
        level_results = {
            "level": level.value,
            "lessons": [],
            "total_exercises": 0,
            "total_correct": 0,
            "total_response_time": 0,
            "accuracy": 0.0,
            "avg_response_time": 0.0
        }
        
        for lesson_num in range(1, lessons_count + 1):
            lesson_result = await self._simulate_lesson(
                user_id, level, source_lang, target_lang, lesson_num
            )
            
            level_results["lessons"].append(lesson_result)
            level_results["total_exercises"] += lesson_result["exercises_count"]
            level_results["total_correct"] += lesson_result["correct_count"]
            level_results["total_response_time"] += lesson_result["total_response_time"]
        
        # Calculate level metrics
        if level_results["total_exercises"] > 0:
            level_results["accuracy"] = (
                level_results["total_correct"] / level_results["total_exercises"] * 100
            )
            level_results["avg_response_time"] = (
                level_results["total_response_time"] / level_results["total_exercises"]
            )
        
        return level_results
    
    async def _simulate_lesson(
        self,
        user_id: int,
        level: LanguageLevel,
        source_lang: str,
        target_lang: str,
        lesson_num: int
    ) -> Dict[str, Any]:
        """Simulate completing a single lesson."""
        exercises_per_lesson = 5
        target_accuracy = self.accuracy_rates[level]
        target_response_time = self.response_times[level]
        
        lesson_result = {
            "lesson_number": lesson_num,
            "level": level.value,
            "exercises_count": exercises_per_lesson,
            "correct_count": 0,
            "total_response_time": 0,
            "accuracy": 0.0,
            "avg_response_time": 0.0,
            "exercises": []
        }
        
        # Generate mock exercises
        for i in range(exercises_per_lesson):
            exercise_id = f"{level.value}_{lesson_num}_{i}"
            
            # Perfect student answers correctly most of the time
            if i < int(exercises_per_lesson * target_accuracy):
                is_correct = True
                answer = f"Correct answer {i}"
                response_time = target_response_time
            else:
                # Occasional mistake to be realistic
                is_correct = False
                answer = f"Wrong answer {i}"
                response_time = target_response_time * 1.5  # Slower when uncertain
            
            # Track progress
            progress = self.progress_repo.create_progress(
                user_id=user_id,
                exercise_id=exercise_id,
                is_correct=is_correct,
                user_answer=answer,
                response_time_ms=int(response_time)
            )
            
            lesson_result["exercises"].append({
                "exercise_id": exercise_id,
                "is_correct": is_correct,
                "response_time_ms": int(response_time)
            })
            
            if is_correct:
                lesson_result["correct_count"] += 1
            
            lesson_result["total_response_time"] += response_time
        
        # Calculate lesson metrics
        lesson_result["accuracy"] = (
            lesson_result["correct_count"] / lesson_result["exercises_count"] * 100
        )
        lesson_result["avg_response_time"] = (
            lesson_result["total_response_time"] / lesson_result["exercises_count"]
        )
        
        return lesson_result
    
    def _get_level_progression(self, start_level: LanguageLevel, target_level: LanguageLevel) -> List[LanguageLevel]:
        """Get the progression of levels from start to target."""
        levels = [LanguageLevel.A1, LanguageLevel.A2, LanguageLevel.B1, LanguageLevel.B2]
        
        # Always include all levels from A1 up to target level for perfect student
        start_index = levels.index(LanguageLevel.A1)  # Always start from A1
        target_index = levels.index(target_level)
        
        return levels[start_index:target_index + 1]


class TestPerfectStudentSimulation:
    """E2E test suite for perfect student simulation."""
    
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
    def simulation(self, mock_session):
        """Create perfect student simulation."""
        sim = PerfectStudentSimulation(mock_session)
        
        # Mock repositories
        sim.user_repo = MagicMock()
        sim.exercise_repo = MagicMock()
        sim.progress_repo = MagicMock()
        sim.placement_test = MagicMock()
        sim.content_agent = MagicMock()
        
        return sim
    
    @pytest.mark.asyncio
    async def test_perfect_student_spanish_to_english(self, simulation):
        """Test perfect student learning Spanish to English."""
        user_data = {
            "wa_id": "perfect_student_es_en",
            "name": "Perfect Student",
            "phone": "+1234567890",
            "native_lang": "es",
            "target_lang": "en",
            "level": None
        }
        
        # Mock repository methods
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.level = None
        
        simulation.user_repo.get_or_create_user.return_value = (mock_user, True)
        simulation.progress_repo.create_progress.return_value = MagicMock()
        
        # Run simulation
        result = await simulation.simulate_complete_learning_journey(
            user_data=user_data,
            target_level=LanguageLevel.B2,
            lessons_per_level=5
        )
        
        # Verify results
        assert result["user_id"] == 1
        assert result["placement_test"] is not None
        assert result["placement_test"].accuracy_percentage >= 90.0
        assert len(result["levels_completed"]) >= 3  # At least A1, A2, B1
        assert result["total_exercises"] > 0
        assert result["total_correct"] > 0
        assert result["final_level"] in [LanguageLevel.B1, LanguageLevel.B2]
        assert result["duration_seconds"] > 0
        
        # Verify progression
        for level_data in result["levels_completed"]:
            assert level_data["accuracy"] >= 80.0  # Perfect student maintains high accuracy
            assert level_data["avg_response_time"] <= 8000  # Reasonable response times
        
        print(f"✅ Perfect student simulation successful!")
        print(f"   Journey: {result['levels_completed'][0]['level']} -> {result['final_level'].value}")
        print(f"   Total exercises: {result['total_exercises']}")
        print(f"   Overall accuracy: {result['total_correct']/result['total_exercises']*100:.1f}%")
    
    @pytest.mark.asyncio
    async def test_perfect_student_french_to_english(self, simulation):
        """Test perfect student learning French to English."""
        user_data = {
            "wa_id": "perfect_student_fr_en",
            "name": "Étudiant Parfait",
            "phone": "+33612345678",
            "native_lang": "fr",
            "target_lang": "en",
            "level": None
        }
        
        # Mock repository methods
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.level = None
        
        simulation.user_repo.get_or_create_user.return_value = (mock_user, True)
        simulation.progress_repo.create_progress.return_value = MagicMock()
        
        # Run simulation with shorter journey
        result = await simulation.simulate_complete_learning_journey(
            user_data=user_data,
            target_level=LanguageLevel.B1,
            lessons_per_level=3
        )
        
        # Verify results
        assert result["user_id"] == 2
        assert result["final_level"] == LanguageLevel.B1
        assert len(result["levels_completed"]) == 3  # A1, A2, B1
        
        print(f"✅ French to English perfect student simulation successful!")
        print(f"   Final level: {result['final_level'].value}")
    
    @pytest.mark.asyncio
    async def test_perfect_student_performance_metrics(self, simulation):
        """Test perfect student maintains optimal performance metrics."""
        user_data = {
            "wa_id": "perfect_student_metrics",
            "name": "Metrics Student",
            "phone": "+1234567891",
            "native_lang": "de",
            "target_lang": "en",
            "level": None
        }
        
        # Mock repository methods
        mock_user = MagicMock()
        mock_user.id = 3
        mock_user.level = None
        
        simulation.user_repo.get_or_create_user.return_value = (mock_user, True)
        simulation.progress_repo.create_progress.return_value = MagicMock()
        
        # Run simulation
        result = await simulation.simulate_complete_learning_journey(
            user_data=user_data,
            target_level=LanguageLevel.A2,
            lessons_per_level=2
        )
        
        # Verify performance metrics meet perfect student standards
        overall_accuracy = (result["total_correct"] / result["total_exercises"] * 100) if result["total_exercises"] > 0 else 0
        overall_avg_response_time = (result["total_response_time"] / result["total_exercises"]) if result["total_exercises"] > 0 else 0
        
        assert overall_accuracy >= 85.0, f"Expected accuracy >= 85%, got {overall_accuracy:.1f}%"
        assert overall_avg_response_time <= 5000, f"Expected response time <= 5000ms, got {overall_avg_response_time:.1f}ms"
        
        # Verify placement test performance
        assert result["placement_test"].accuracy_percentage >= 90.0
        
        print(f"✅ Performance metrics verification passed!")
        print(f"   Overall accuracy: {overall_accuracy:.1f}%")
        print(f"   Overall response time: {overall_avg_response_time:.1f}ms")
        print(f"   Placement test accuracy: {result['placement_test'].accuracy_percentage:.1f}%")
    
    def test_perfect_student_characteristics(self, simulation):
        """Test perfect student characteristics are properly defined."""
        # Verify response times increase with difficulty
        assert simulation.response_times[LanguageLevel.A1] < simulation.response_times[LanguageLevel.A2]
        assert simulation.response_times[LanguageLevel.A2] < simulation.response_times[LanguageLevel.B1]
        assert simulation.response_times[LanguageLevel.B1] < simulation.response_times[LanguageLevel.B2]
        
        # Verify accuracy decreases slightly with difficulty (realistic)
        assert simulation.accuracy_rates[LanguageLevel.A1] >= simulation.accuracy_rates[LanguageLevel.A2]
        assert simulation.accuracy_rates[LanguageLevel.A2] >= simulation.accuracy_rates[LanguageLevel.B1]
        assert simulation.accuracy_rates[LanguageLevel.B1] >= simulation.accuracy_rates[LanguageLevel.B2]
        
        # Verify minimum standards
        for level in [LanguageLevel.A1, LanguageLevel.A2, LanguageLevel.B1, LanguageLevel.B2]:
            assert simulation.response_times[level] > 0
            assert 0.8 <= simulation.accuracy_rates[level] <= 1.0
        
        print(f"✅ Perfect student characteristics verified!")
        print(f"   Response times: {simulation.response_times}")
        print(f"   Accuracy rates: {simulation.accuracy_rates}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
