"""End-to-End Tests for Curriculum Generation Pipeline

Tests the complete curriculum generation system in realistic scenarios:
- Full pipeline execution with real database
- Performance testing with larger batches
- Error recovery and retry mechanisms
- Database consistency and integrity
- Real-world usage patterns
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from orchestrator.content_orchestrator import ContentOrchestrator
from services.curriculum.parser import get_mvp_generation_specs

class TestCurriculumGenerationE2E:
    """End-to-end tests for curriculum generation."""
    
    @pytest.fixture
    def production_database(self):
        """Create production-like database for E2E testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Initialize complete database
        from scripts.init_curriculum_database import init_curriculum_database
        from scripts.init_exercise_schemas import create_exercise_schemas_table, populate_exercise_schemas
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        init_curriculum_database(f"sqlite:///{path}")
        
        engine = create_engine(f"sqlite:///{path}")
        SessionLocal = sessionmaker(bind=engine)
        create_exercise_schemas_table(engine)
        populate_exercise_schemas(SessionLocal())
        
        yield f"sqlite:///{path}"
        
        if os.path.exists(path):
            os.unlink(path)
    
    def test_full_curriculum_structure_validation(self, production_database):
        """Test complete curriculum structure is properly initialized."""
        from services.curriculum.parser import CurriculumStructureParser
        
        parser = CurriculumStructureParser(production_database)
        
        # Validate all combinations exist
        combinations = parser.parse_curriculum_from_database()
        assert len(combinations) == 54
        
        # Validate MVP distribution
        specs = parser.extract_generation_specs(combinations)
        lang_distribution = {}
        for spec in specs:
            lang_pair = spec.language_pair_name
            lang_distribution[lang_pair] = lang_distribution.get(lang_pair, 0) + 1
        
        assert lang_distribution['Spanish → English'] == 27
        assert lang_distribution['Portuguese → English'] == 27
        
        # Validate category distribution
        category_distribution = {}
        for spec in specs:
            category = spec.category
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        assert category_distribution['Vocabulary'] == 18
        assert category_distribution['Grammar'] == 18
        assert category_distribution['Functional Language'] == 18
    
    def test_exercise_schema_completeness(self, production_database):
        """Test all exercise schemas are properly defined."""
        orchestrator = ContentOrchestrator(production_database)
        
        from services.curriculum.curriculum_database import ExerciseTypeID
        
        # Test all exercise types have schemas
        exercise_types = [
            ExerciseTypeID.MULTIPLE_CHOICE,
            ExerciseTypeID.FILL_IN_BLANK,
            ExerciseTypeID.ROLEPLAY,
            ExerciseTypeID.TRANSLATION,
            ExerciseTypeID.ERROR_IDENTIFICATION,
            ExerciseTypeID.OPEN_RESPONSE
        ]
        
        for ex_type in exercise_types:
            schema = orchestrator.get_schema_for_exercise_type(ex_type)
            
            # Validate required fields
            assert hasattr(schema, 'exercise_type')
            assert hasattr(schema, 'field_theory_description')
            assert hasattr(schema, 'field_introduction_description')
            assert hasattr(schema, 'field_input_description')
            assert hasattr(schema, 'field_output_description')
            assert hasattr(schema, 'validation_rules')
            
            # Validate field content
            assert len(schema.field_theory_description) > 10
            assert len(schema.field_introduction_description) > 10
            assert len(schema.field_input_description) > 10
            assert len(schema.field_output_description) > 10
            assert len(schema.example_theory) > 10
            assert len(schema.example_input) > 10
            assert len(schema.example_output) > 1
    
    @patch('orchestrator.content_orchestrator.SchemaAwareGenerator')
    def test_large_batch_generation(self, mock_generator_class, production_database):
        """Test generation with larger batch sizes."""
        # Mock successful generation
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.theory = f"Large batch test theory"
        mock_result.exercise_introduction = "Large batch test introduction"
        mock_result.exercise_input = "Large batch test input"
        mock_result.expected_output = "Large batch test output"
        mock_generator.generate_with_schema.return_value = mock_result
        
        # Create orchestrator
        orchestrator = ContentOrchestrator(production_database)
        orchestrator.llm_generator = mock_generator
        
        # Test large batch
        start_time = time.time()
        results = orchestrator.orchestrate_content_generation(
            batch_size=10, 
            variations_per_combo=5
        )
        end_time = time.time()
        
        # Verify results
        assert results.total_requested == 50  # 10 combos × 5 variations
        assert results.successful == 50
        assert results.failed == 0
        assert len(results.exercises) == 50
        
        # Verify performance (should complete in reasonable time)
        duration = end_time - start_time
        assert duration < 30  # Should complete within 30 seconds
        
        # Verify LLM called correct number of times
        assert mock_generator.generate_with_schema.call_count == 50
        
        # Verify database consistency
        stats = orchestrator.exercise_repo.get_exercise_statistics()
        assert stats['total_exercises'] == 50
    
    @patch('orchestrator.content_orchestrator.SchemaAwareGenerator')
    def test_partial_failure_recovery(self, mock_generator_class, production_database):
        """Test system handles partial failures gracefully."""
        # Mock generator with intermittent failures
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        def mock_generate_with_variation(spec, schema, variation_num=0):
            result = Mock()
            # Fail on odd variation numbers
            if variation_num % 2 == 1:
                result.success = False
                result.error_message = f"Simulated failure for variation {variation_num}"
            else:
                result.success = True
                result.theory = f"Success theory for variation {variation_num}"
                result.exercise_introduction = "Success introduction"
                result.exercise_input = "Success input"
                result.expected_output = "Success output"
            return result
        
        mock_generator.generate_with_schema.side_effect = mock_generate_with_variation
        
        # Create orchestrator
        orchestrator = ContentOrchestrator(production_database)
        orchestrator.llm_generator = mock_generator
        
        # Run with failures
        results = orchestrator.orchestrate_content_generation(
            batch_size=3, 
            variations_per_combo=4
        )
        
        # Verify partial success
        assert results.total_requested == 12  # 3 combos × 4 variations
        assert results.successful == 6  # Even variations succeed
        assert results.failed == 6  # Odd variations fail
        assert len(results.exercises) == 6
        assert len(results.errors) == 6
        
        # Verify error messages
        for error in results.errors:
            assert "Simulated failure" in error
        
        # Verify database contains only successful exercises
        stats = orchestrator.exercise_repo.get_exercise_statistics()
        assert stats['total_exercises'] == 6
    
    def test_database_consistency_under_load(self, production_database):
        """Test database remains consistent under concurrent operations."""
        orchestrator = ContentOrchestrator(production_database)
        
        # Simulate concurrent status updates
        pending_specs = orchestrator.curriculum_parser.get_pending_combinations(limit=5)
        
        # Update statuses in different orders
        for i, spec in enumerate(pending_specs):
            orchestrator.curriculum_parser.update_generation_status(
                spec.id, "in_progress"
            )
        
        # Verify all statuses updated correctly
        updated_specs = orchestrator.curriculum_parser.parse_curriculum_from_database()
        in_progress_count = sum(1 for spec in updated_specs if spec.status == 'in_progress')
        assert in_progress_count == 5
        
        # Test status transitions
        for spec in pending_specs:
            orchestrator.curriculum_parser.update_generation_status(
                spec.id, "completed", 10
            )
        
        # Verify final state
        final_specs = orchestrator.curriculum_parser.parse_curriculum_from_database()
        completed_count = sum(1 for spec in final_specs if spec.status == 'completed')
        assert completed_count == 5
    
    @patch('orchestrator.content_orchestrator.SchemaAwareGenerator')
    def test_variation_uniqueness(self, mock_generator_class, production_database):
        """Test that variations generate unique content."""
        # Mock generator that creates unique content per variation
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        def mock_generate_unique(spec, schema, variation_num=0):
            result = Mock()
            result.success = True
            result.theory = f"Unique theory for variation {variation_num}"
            result.exercise_introduction = f"Unique introduction for variation {variation_num}"
            result.exercise_input = f"Unique input for variation {variation_num}"
            result.expected_output = f"Unique output for variation {variation_num}"
            return result
        
        mock_generator.generate_with_schema.side_effect = mock_generate_unique
        
        # Create orchestrator
        orchestrator = ContentOrchestrator(production_database)
        orchestrator.llm_generator = mock_generator
        
        # Generate variations
        results = orchestrator.orchestrate_content_generation(
            batch_size=1, 
            variations_per_combo=10
        )
        
        # Verify uniqueness
        assert len(results.exercises) == 10
        
        # Check all exercises have unique content
        theories = [ex.theory for ex in results.exercises]
        introductions = [ex.exercise_introduction for ex in results.exercises]
        inputs = [ex.exercise_input for ex in results.exercises]
        outputs = [ex.expected_output for ex in results.exercises]
        
        assert len(set(theories)) == 10
        assert len(set(introductions)) == 10
        assert len(set(inputs)) == 10
        assert len(set(outputs)) == 10
        
        # Verify unique exercise IDs
        exercise_ids = [ex.curriculum_combo_id for ex in results.exercises]
        assert len(set(exercise_ids)) == 10
    
    def test_mvp_completion_scenario(self, production_database):
        """Test complete MVP curriculum generation scenario."""
        from services.curriculum.curriculum_database import ExerciseTypeID
        
        # Mock generator for MVP completion
        with patch('orchestrator.content_orchestrator.SchemaAwareGenerator') as mock_gen_class:
            mock_generator = Mock()
            mock_gen_class.return_value = mock_generator
            
            mock_result = Mock()
            mock_result.success = True
            mock_result.theory = "MVP completion theory"
            mock_result.exercise_introduction = "MVP completion introduction"
            mock_result.exercise_input = "MVP completion input"
            mock_result.expected_output = "MVP completion output"
            mock_generator.generate_with_schema.return_value = mock_result
            
            # Create orchestrator
            orchestrator = ContentOrchestrator(production_database)
            orchestrator.llm_generator = mock_generator
            
            # Generate MVP curriculum (small subset for testing)
            results = orchestrator.orchestrate_content_generation(
                batch_size=5, 
                variations_per_combo=3
            )
            
            # Verify MVP generation
            assert results.successful == 15  # 5 combos × 3 variations
            assert len(results.exercises) == 15
            
            # Verify MVP exercise type distribution
            exercise_types = [ex.exercise_type_id for ex in results.exercises]
            type_counts = {ex_type: exercise_types.count(ex_type) for ex_type in set(exercise_types)}
            
            # Should have variety of exercise types
            assert len(type_counts) >= 2
            
            # Verify database state
            stats = orchestrator.exercise_repo.get_exercise_statistics()
            assert stats['total_exercises'] == 15
            
            # Verify curriculum structure status
            final_stats = orchestrator.get_generation_statistics()
            assert final_stats['completed'] == 5
            assert final_stats['pending'] == 49  # 54 - 5 completed
    
    def test_pipeline_resilience(self, production_database):
        """Test pipeline resilience to various error conditions."""
        orchestrator = ContentOrchestrator(production_database)
        
        # Test with empty batch
        results = orchestrator.orchestrate_content_generation(batch_size=0)
        assert results.total_requested == 0
        assert results.total_generated == 0
        
        # Test with negative batch size
        results = orchestrator.orchestrate_content_generation(batch_size=-1)
        assert results.total_requested == 0
        
        # Test with zero variations
        with patch('orchestrator.content_orchestrator.SchemaAwareGenerator') as mock_gen_class:
            mock_generator = Mock()
            mock_gen_class.return_value = mock_generator
            mock_result = Mock()
            mock_result.success = True
            mock_result.theory = "Zero variations test"
            mock_result.exercise_introduction = "Test intro"
            mock_result.exercise_input = "Test input"
            mock_result.expected_output = "Test output"
            mock_generator.generate_with_schema.return_value = mock_result
            
            orchestrator.llm_generator = mock_generator
            results = orchestrator.orchestrate_content_generation(
                batch_size=2, 
                variations_per_combo=0
            )
            
            assert results.total_requested == 0
            assert results.successful == 0
    
    def test_database_transaction_integrity(self, production_database):
        """Test database transaction integrity during failures."""
        from services.curriculum.parser import CurriculumStructureParser
        
        parser = CurriculumStructureParser(production_database)
        
        # Get initial state
        initial_specs = parser.parse_curriculum_from_database()
        initial_count = len(initial_specs)
        
        # Simulate failed transaction
        try:
            # This should fail and rollback
            parser.update_generation_status("INVALID_ID", "completed")
        except:
            pass
        
        # Verify database state unchanged
        final_specs = parser.parse_curriculum_from_database()
        assert len(final_specs) == initial_count
        
        # Verify no corruption
        for spec in final_specs:
            assert hasattr(spec, 'id')
            assert hasattr(spec, 'status')
            assert spec.status in ['pending', 'in_progress', 'completed', 'failed']

class TestPerformanceE2E:
    """Performance-focused end-to-end tests."""
    
    @pytest.fixture
    def performance_database(self):
        """Create optimized database for performance testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Initialize database
        from scripts.init_curriculum_database import init_curriculum_database
        from scripts.init_exercise_schemas import create_exercise_schemas_table, populate_exercise_schemas
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        init_curriculum_database(f"sqlite:///{path}")
        
        engine = create_engine(f"sqlite:///{path}")
        SessionLocal = sessionmaker(bind=engine)
        create_exercise_schemas_table(engine)
        populate_exercise_schemas(SessionLocal())
        
        yield f"sqlite:///{path}"
        
        if os.path.exists(path):
            os.unlink(path)
    
    @patch('orchestrator.content_orchestrator.SchemaAwareGenerator')
    def test_scalability_performance(self, mock_generator_class, performance_database):
        """Test system scalability with increasing load."""
        # Mock fast generation
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.theory = "Performance test theory"
        mock_result.exercise_introduction = "Performance test introduction"
        mock_result.exercise_input = "Performance test input"
        mock_result.expected_output = "Performance test output"
        mock_generator.generate_with_schema.return_value = mock_result
        
        orchestrator = ContentOrchestrator(performance_database)
        orchestrator.llm_generator = mock_generator
        
        # Test scalability with different batch sizes
        batch_sizes = [1, 5, 10]
        variations_per_combo = 5
        
        for batch_size in batch_sizes:
            start_time = time.time()
            results = orchestrator.orchestrate_content_generation(
                batch_size=batch_size,
                variations_per_combo=variations_per_combo
            )
            end_time = time.time()
            
            duration = end_time - start_time
            expected_exercises = batch_size * variations_per_combo
            
            assert results.successful == expected_exercises
            assert duration < 10  # Should complete quickly
            assert len(results.errors) == 0
            
            # Performance should scale reasonably
            exercises_per_second = expected_exercises / duration
            assert exercises_per_second > 1  # At least 1 exercise per second

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
