"""Load Testing Content Factory.

This module provides load testing capabilities for the content generation system,
simulating high-volume concurrent requests to test system performance and scalability.
"""

import pytest
import asyncio
import time
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

from src.orchestrator.curriculum_seed import CurriculumSeedGenerator
from src.services.llm.content_generation import ContentGenerationAgent
from src.data.models import LanguageLevel, ExerciseType, Topic
from src.data.repositories.exercise import ExerciseRepository
from src.data.repositories.user import UserRepository
from src.data.repositories.user_progress import UserProgressRepository
from sqlalchemy.orm import Session


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    total_exercises_generated: int
    exercises_per_second: float
    errors: List[str]
    start_time: float
    end_time: float
    duration_seconds: float
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100


class LoadTestingContentFactory:
    """Factory for load testing content generation under various conditions."""
    
    def __init__(self, db_session: Session):
        """Initialize the load testing factory."""
        self.db_session = db_session
        self.content_agent = ContentGenerationAgent(db_session)
        self.exercise_repo = ExerciseRepository(db_session)
        self.user_repo = UserRepository(db_session)
        self.progress_repo = UserProgressRepository(db_session)
        
        # Load test scenarios
        self.scenarios = {
            "light_load": {"concurrent_users": 5, "requests_per_user": 10},
            "moderate_load": {"concurrent_users": 20, "requests_per_user": 25},
            "heavy_load": {"concurrent_users": 50, "requests_per_user": 50},
            "stress_test": {"concurrent_users": 100, "requests_per_user": 100},
            "burst_test": {"concurrent_users": 200, "requests_per_user": 25}
        }
        
        # Test parameters
        self.language_pairs = [
            ("es", "en"), ("en", "es"), ("fr", "en"), ("en", "fr"),
            ("de", "en"), ("en", "de"), ("pt", "en"), ("en", "pt"),
            ("it", "en"), ("en", "it")
        ]
        
        self.levels = [LanguageLevel.A1, LanguageLevel.A2, LanguageLevel.B1, LanguageLevel.B2]
        self.exercise_types = list(ExerciseType)
        
        # Sample topics for testing
        self.sample_topics = [
            "Daily Routines", "Food and Dining", "Travel", "Work",
            "Family", "Shopping", "Weather", "Hobbies", "Health", "Technology"
        ]
    
    async def run_load_test(
        self,
        scenario_name: str,
        duration_seconds: Optional[int] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> LoadTestMetrics:
        """
        Run a load test scenario.
        
        Args:
            scenario_name: Name of the predefined scenario
            duration_seconds: Optional time limit for the test
            custom_config: Override scenario configuration
            
        Returns:
            Load test metrics
        """
        config = self.scenarios.get(scenario_name, {})
        if custom_config:
            config.update(custom_config)
        
        print(f"🚀 Starting load test: {scenario_name}")
        print(f"   Concurrent users: {config.get('concurrent_users', 0)}")
        print(f"   Requests per user: {config.get('requests_per_user', 0)}")
        
        metrics = LoadTestMetrics(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            average_response_time_ms=0.0,
            min_response_time_ms=float('inf'),
            max_response_time_ms=0.0,
            total_exercises_generated=0,
            exercises_per_second=0.0,
            errors=[],
            start_time=time.time(),
            end_time=0.0,
            duration_seconds=0.0
        )
        
        response_times = []
        
        async def user_session(user_id: int) -> Dict[str, Any]:
            """Simulate a single user session."""
            user_metrics = {
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "response_times": [],
                "exercises_generated": 0,
                "errors": []
            }
            
            requests_per_user = config.get('requests_per_user', 10)
            
            for request_num in range(requests_per_user):
                try:
                    # Random test parameters
                    source_lang, target_lang = random.choice(self.language_pairs)
                    level = random.choice(self.levels)
                    exercise_type = random.choice(self.exercise_types)
                    topic = random.choice(self.sample_topics)
                    
                    # Measure response time
                    start_time = time.time()
                    
                    # Simulate content generation
                    result = await self._simulate_content_generation(
                        source_lang, target_lang, level, exercise_type, topic
                    )
                    
                    response_time = (time.time() - start_time) * 1000
                    user_metrics["response_times"].append(response_time)
                    user_metrics["requests"] += 1
                    user_metrics["successful"] += 1
                    user_metrics["exercises_generated"] += result.get("exercises_count", 1)
                    
                except Exception as e:
                    user_metrics["requests"] += 1
                    user_metrics["failed"] += 1
                    user_metrics["errors"].append(str(e))
            
            return user_metrics
        
        # Run concurrent user sessions
        concurrent_users = config.get('concurrent_users', 5)
        tasks = []
        
        for user_id in range(concurrent_users):
            task = asyncio.create_task(user_session(user_id))
            tasks.append(task)
        
        # Wait for all sessions to complete or timeout
        try:
            if duration_seconds:
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=duration_seconds)
            else:
                await asyncio.gather(*tasks)
        except asyncio.TimeoutError:
            print(f"⏰ Load test timed out after {duration_seconds} seconds")
        
        # Aggregate metrics
        for task in tasks:
            if task.done():
                user_metrics = task.result()
                metrics.total_requests += user_metrics["requests"]
                metrics.successful_requests += user_metrics["successful"]
                metrics.failed_requests += user_metrics["failed"]
                metrics.total_exercises_generated += user_metrics["exercises_generated"]
                metrics.errors.extend(user_metrics["errors"])
                response_times.extend(user_metrics["response_times"])
        
        # Calculate final metrics
        metrics.end_time = time.time()
        metrics.duration_seconds = metrics.end_time - metrics.start_time
        
        if response_times:
            metrics.average_response_time_ms = sum(response_times) / len(response_times)
            metrics.min_response_time_ms = min(response_times)
            metrics.max_response_time_ms = max(response_times)
        
        if metrics.duration_seconds > 0:
            metrics.exercises_per_second = metrics.total_exercises_generated / metrics.duration_seconds
        
        return metrics
    
    async def _simulate_content_generation(
        self,
        source_lang: str,
        target_lang: str,
        level: LanguageLevel,
        exercise_type: ExerciseType,
        topic: str
    ) -> Dict[str, Any]:
        """
        Simulate content generation with realistic timing.
        
        Returns:
            Dictionary with generation results
        """
        # Simulate processing time based on complexity
        base_time = 0.5  # Base 500ms
        complexity_multiplier = {
            LanguageLevel.A1: 1.0,
            LanguageLevel.A2: 1.2,
            LanguageLevel.B1: 1.5,
            LanguageLevel.B2: 2.0
        }
        
        type_multiplier = {
            ExerciseType.MULTIPLE_CHOICE: 1.0,
            ExerciseType.TRANSLATION: 1.1,
            ExerciseType.FILL_IN_BLANK: 1.2,
            ExerciseType.LISTENING: 1.3,
            ExerciseType.SPEAKING: 1.4,
            ExerciseType.ROLEPLAY: 2.0
        }
        
        processing_time = (
            base_time * 
            complexity_multiplier.get(level, 1.0) * 
            type_multiplier.get(exercise_type, 1.0)
        )
        
        # Add random variation
        processing_time *= random.uniform(0.8, 1.5)
        
        # Simulate processing
        await asyncio.sleep(processing_time)
        
        # Simulate occasional failures (5% failure rate)
        if random.random() < 0.05:
            raise Exception("Simulated content generation failure")
        
        # Return mock result
        exercises_count = random.randint(1, 5)
        
        return {
            "exercises_count": exercises_count,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "level": level.value,
            "exercise_type": exercise_type.value,
            "topic": topic,
            "processing_time_ms": processing_time * 1000
        }
    
    async def run_comprehensive_load_tests(self) -> Dict[str, LoadTestMetrics]:
        """
        Run all predefined load test scenarios.
        
        Returns:
            Dictionary mapping scenario names to their metrics
        """
        print("🧪 Starting comprehensive load testing suite...")
        
        results = {}
        
        for scenario_name in self.scenarios.keys():
            print(f"\n{'='*50}")
            metrics = await self.run_load_test(scenario_name)
            results[scenario_name] = metrics
            
            # Print scenario results
            print(f"📊 {scenario_name} Results:")
            print(f"   Total requests: {metrics.total_requests}")
            print(f"   Success rate: {metrics.success_rate:.1f}%")
            print(f"   Average response time: {metrics.average_response_time_ms:.1f}ms")
            print(f"   Exercises generated: {metrics.total_exercises_generated}")
            print(f"   Exercises per second: {metrics.exercises_per_second:.1f}")
            print(f"   Duration: {metrics.duration_seconds:.1f}s")
            
            if metrics.error_rate > 0:
                print(f"   Errors: {len(metrics.errors)} ({metrics.error_rate:.1f}%)")
        
        return results
    
    def analyze_performance_trends(self, results: Dict[str, LoadTestMetrics]) -> Dict[str, Any]:
        """
        Analyze performance trends across different load scenarios.
        
        Args:
            results: Load test results from multiple scenarios
            
        Returns:
            Performance analysis
        """
        analysis = {
            "scalability": {},
            "performance_degradation": {},
            "bottlenecks": [],
            "recommendations": []
        }
        
        # Sort scenarios by load (concurrent users)
        sorted_scenarios = sorted(
            results.items(),
            key=lambda x: self.scenarios.get(x[0], {}).get('concurrent_users', 0)
        )
        
        if len(sorted_scenarios) < 2:
            return analysis
        
        # Analyze scalability
        for i, (scenario_name, metrics) in enumerate(sorted_scenarios):
            concurrent_users = self.scenarios.get(scenario_name, {}).get('concurrent_users', 0)
            
            analysis["scalability"][scenario_name] = {
                "concurrent_users": concurrent_users,
                "exercises_per_second": metrics.exercises_per_second,
                "success_rate": metrics.success_rate,
                "avg_response_time": metrics.average_response_time_ms
            }
        
        # Check for performance degradation
        baseline = sorted_scenarios[0][1]  # Lightest load as baseline
        
        for scenario_name, metrics in sorted_scenarios[1:]:
            response_time_degradation = (
                (metrics.average_response_time_ms - baseline.average_response_time_ms) / 
                baseline.average_response_time_ms * 100
            )
            
            success_rate_degradation = baseline.success_rate - metrics.success_rate
            
            analysis["performance_degradation"][scenario_name] = {
                "response_time_degradation_percent": response_time_degradation,
                "success_rate_degradation_percent": success_rate_degradation
            }
            
            # Identify bottlenecks
            if response_time_degradation > 100:  # >100% increase in response time
                analysis["bottlenecks"].append(
                    f"{scenario_name}: Response time increased by {response_time_degradation:.1f}%"
                )
            
            if success_rate_degradation > 10:  # >10% decrease in success rate
                analysis["bottlenecks"].append(
                    f"{scenario_name}: Success rate decreased by {success_rate_degradation:.1f}%"
                )
        
        # Generate recommendations
        max_concurrent = max(
            self.scenarios.get(name, {}).get('concurrent_users', 0)
            for name in results.keys()
        )
        
        if max_concurrent < 50:
            analysis["recommendations"].append("System can handle light to moderate loads well")
        
        if any(metrics.success_rate < 95 for metrics in results.values()):
            analysis["recommendations"].append("Consider implementing retry mechanisms for failed requests")
        
        if any(metrics.average_response_time_ms > 5000 for metrics in results.values()):
            analysis["recommendations"].append("Optimize content generation for better response times")
        
        return analysis


class TestLoadTestingContentFactory:
    """Test suite for load testing content factory."""
    
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
    def factory(self, mock_session):
        """Create load testing factory."""
        return LoadTestingContentFactory(mock_session)
    
    @pytest.mark.asyncio
    async def test_light_load_scenario(self, factory):
        """Test light load scenario."""
        metrics = await factory.run_load_test("light_load")
        
        # Verify basic metrics
        assert metrics.total_requests > 0
        assert metrics.successful_requests > 0
        assert metrics.success_rate >= 80.0  # At least 80% success rate
        assert metrics.average_response_time_ms > 0
        assert metrics.duration_seconds > 0
        
        print(f"✅ Light load test passed!")
        print(f"   Requests: {metrics.total_requests}")
        print(f"   Success rate: {metrics.success_rate:.1f}%")
        print(f"   Avg response time: {metrics.average_response_time_ms:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_moderate_load_scenario(self, factory):
        """Test moderate load scenario."""
        metrics = await factory.run_load_test("moderate_load")
        
        # Verify metrics are reasonable
        assert metrics.total_requests >= 400  # 20 users * 20 requests
        assert metrics.success_rate >= 70.0  # At least 70% success rate under moderate load
        assert metrics.exercises_per_second > 0
        
        print(f"✅ Moderate load test passed!")
        print(f"   Requests: {metrics.total_requests}")
        print(f"   Success rate: {metrics.success_rate:.1f}%")
        print(f"   Exercises/sec: {metrics.exercises_per_second:.1f}")
    
    @pytest.mark.asyncio
    async def test_custom_load_config(self, factory):
        """Test custom load configuration."""
        custom_config = {
            "concurrent_users": 3,
            "requests_per_user": 5
        }
        
        metrics = await factory.run_load_test("custom_test", custom_config=custom_config)
        
        # Verify custom configuration was applied
        assert metrics.total_requests == 15  # 3 users * 5 requests
        assert metrics.successful_requests <= 15
        assert metrics.failed_requests <= 15
        
        print(f"✅ Custom load test passed!")
        print(f"   Custom requests: {metrics.total_requests}")
    
    @pytest.mark.asyncio
    async def test_content_generation_simulation(self, factory):
        """Test content generation simulation."""
        result = await factory._simulate_content_generation(
            source_lang="es",
            target_lang="en",
            level=LanguageLevel.A1,
            exercise_type=ExerciseType.MULTIPLE_CHOICE,
            topic="Daily Routines"
        )
        
        # Verify simulation results
        assert "exercises_count" in result
        assert result["exercises_count"] >= 1
        assert result["source_lang"] == "es"
        assert result["target_lang"] == "en"
        assert result["level"] == "A1"
        assert result["exercise_type"] == "multiple_choice"
        assert result["topic"] == "Daily Routines"
        
        print(f"✅ Content generation simulation passed!")
        print(f"   Generated {result['exercises_count']} exercises")
    
    def test_load_test_metrics_calculation(self, factory):
        """Test load test metrics calculations."""
        metrics = LoadTestMetrics(
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            average_response_time_ms=1500.0,
            min_response_time_ms=500.0,
            max_response_time_ms=3000.0,
            total_exercises_generated=200,
            exercises_per_second=10.0,
            errors=["Error 1", "Error 2"],
            start_time=1000.0,
            end_time=1010.0,
            duration_seconds=10.0
        )
        
        # Verify calculations
        assert metrics.success_rate == 95.0
        assert metrics.error_rate == 5.0
        
        print(f"✅ Metrics calculation test passed!")
        print(f"   Success rate: {metrics.success_rate}%")
        print(f"   Error rate: {metrics.error_rate}%")
    
    def test_performance_analysis(self, factory):
        """Test performance analysis functionality."""
        # Create mock results
        results = {
            "light_load": LoadTestMetrics(
                total_requests=50, successful_requests=48, failed_requests=2,
                average_response_time_ms=800.0, min_response_time_ms=500.0,
                max_response_time_ms=1200.0, total_exercises_generated=100,
                exercises_per_second=10.0, errors=[], start_time=0.0,
                end_time=10.0, duration_seconds=10.0
            ),
            "heavy_load": LoadTestMetrics(
                total_requests=2500, successful_requests=2000, failed_requests=500,
                average_response_time_ms=2000.0, min_response_time_ms=800.0,
                max_response_time_ms=5000.0, total_exercises_generated=4000,
                exercises_per_second=200.0, errors=["Error"] * 500,
                start_time=0.0, end_time=20.0, duration_seconds=20.0
            )
        }
        
        analysis = factory.analyze_performance_trends(results)
        
        # Verify analysis structure
        assert "scalability" in analysis
        assert "performance_degradation" in analysis
        assert "bottlenecks" in analysis
        assert "recommendations" in analysis
        
        print(f"✅ Performance analysis test passed!")
        print(f"   Scalability metrics: {len(analysis['scalability'])}")
        print(f"   Bottlenecks identified: {len(analysis['bottlenecks'])}")
        print(f"   Recommendations: {len(analysis['recommendations'])}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
