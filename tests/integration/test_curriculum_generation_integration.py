"""Integration Tests for Curriculum Generation Pipeline

Tests the interaction between components of the curriculum generation system:
- Database operations and parser integration
- Orchestrator and schema registry integration
- End-to-end pipeline with mocked LLM calls
- Error handling and recovery scenarios
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.curriculum.parser import CurriculumStructureParser
from orchestrator.content_orchestrator import ContentOrchestrator
from services.llm.schema_aware_generator import SchemaAwareGenerator
from data.repositories.exercise_repo import ExerciseRepository
from services.curriculum.curriculum_database import ExerciseTypeID

class TestDatabaseParserIntegration:
    """Integration tests for database and parser components."""
    
    @pytest.fixture
    def temp_database(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Initialize database
        from scripts.init_curriculum_database import init_curriculum_database
        init_curriculum_database(f"sqlite:///{path}")
        
        yield f"sqlite:///{path}"
        
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)
    
    def test_parser_database_integration(self, temp_database):
        """Test parser integration with database."""
        parser = CurriculumStructureParser(temp_database)
        
        # Test parsing
        combinations = parser.parse_curriculum_from_database()
        assert len(combinations) == 54
        
        # Test generation specs
        specs = parser.extract_generation_specs(combinations)
        assert len(specs) == 54
        
        # Test status updates
        pending = parser.get_pending_combinations(limit=1)
        assert len(pending) == 1
        
        # Update status
        success = parser.update_generation_status(pending[0].id, "in_progress")
        assert success is True
        
        # Verify status change
        updated_pending = parser.get_pending_combinations(limit=10)
        assert len(updated_pending) == 53  # One less pending

class TestOrchestratorSchemaIntegration:
    """Integration tests for orchestrator and schema registry."""
    
    @pytest.fixture
    def full_database(self):
        """Create fully initialized database."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Initialize curriculum database
        from scripts.init_curriculum_database import init_curriculum_database
        init_curriculum_database(f"sqlite:///{path}")
        
        # Initialize exercise schemas
        from scripts.init_exercise_schemas import create_exercise_schemas_table, populate_exercise_schemas
        engine = create_engine(f"sqlite:///{path}")
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=engine)
        create_exercise_schemas_table(engine)
        populate_exercise_schemas(SessionLocal())
        
        yield f"sqlite:///{path}"
        
        if os.path.exists(path):
            os.unlink(path)
    
    def test_orchestrator_schema_retrieval(self, full_database):
        """Test orchestrator can retrieve schemas correctly."""
        orchestrator = ContentOrchestrator(full_database)
        
        # Test schema retrieval for all exercise types
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
            assert schema is not None
            assert schema.exercise_type is not None
            assert schema.field_theory_description is not None
    
    def test_orchestrator_statistics_integration(self, full_database):
        """Test orchestrator statistics integration."""
        orchestrator = ContentOrchestrator(full_database)
        
        stats = orchestrator.get_generation_statistics()
        assert stats['total_combinations'] == 54
        assert stats['pending'] == 54
        assert stats['completed'] == 0
        assert stats['failed'] == 0
        
        # Test queue info
        queue_count = orchestrator.get_pending_count()
        assert queue_count == 54

class TestLLMGeneratorIntegration:
    """Integration tests for LLM generator with other components."""
    
    @pytest.fixture
    def mock_generator(self):
        """Create mock LLM generator."""
        generator = Mock(spec=SchemaAwareGenerator)
        
        # Mock generation result
        mock_result = Mock()
        mock_result.success = True
        mock_result.theory = "Test theory content"
        mock_result.exercise_introduction = "Test introduction"
        mock_result.exercise_input = "Test input content"
        mock_result.expected_output = "Test expected output"
        mock_result.error_message = None
        
        generator.generate_with_schema.return_value = mock_result
        return generator
    
    def test_generator_prompt_building(self):
        """Test LLM generator prompt building integration."""
        generator = SchemaAwareGenerator()
        
        # Mock spec and schema
        mock_spec = Mock()
        mock_spec.language_pair = ('es', 'en')
        mock_spec.level = 'B1'
        mock_spec.exercise_type = 'multiple_choice'
        mock_spec.topic = 'Daily Life'
        mock_spec.category = 'Vocabulary'
        
        mock_schema = Mock()
        mock_schema.field_theory_description = "Theory description"
        mock_schema.field_introduction_description = "Intro description"
        mock_schema.field_input_description = "Input description"
        mock_schema.field_output_description = "Output description"
        mock_schema.example_theory = "Example theory"
        mock_schema.example_introduction = "Example intro"
        mock_schema.example_input = "Example input"
        mock_schema.example_output = "Example output"
        
        # Test prompt building with variation
        prompt = generator.build_context_aware_prompt(mock_spec, mock_schema, variation_num=2)
        
        # Verify prompt contains all required elements
        assert "Spanish" in prompt
        assert "English" in prompt
        assert "B1" in prompt
        assert "multiple_choice" in prompt
        assert "Daily Life" in prompt
        assert "VARIATION SEED: 2" in prompt
        assert "completely different exercise" in prompt

class TestExerciseStorageIntegration:
    """Integration tests for exercise storage with pipeline."""
    
    @pytest.fixture
    def storage_database(self):
        """Create database with exercise storage."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Initialize curriculum database
        from scripts.init_curriculum_database import init_curriculum_database
        init_curriculum_database(f"sqlite:///{path}")
        
        # Initialize exercise schemas
        from scripts.init_exercise_schemas import create_exercise_schemas_table, populate_exercise_schemas
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(f"sqlite:///{path}")
        SessionLocal = sessionmaker(bind=engine)
        create_exercise_schemas_table(engine)
        populate_exercise_schemas(SessionLocal())
        
        yield f"sqlite:///{path}"
        
        if os.path.exists(path):
            os.unlink(path)
    
    def test_exercise_storage_pipeline(self, storage_database):
        """Test exercise storage integration with pipeline."""
        repo = ExerciseRepository(storage_database)
        
        # Test saving multiple exercises
        exercises_data = [
            {
                'source_lang': 'es',
                'target_lang': 'en',
                'difficulty_level': 'B1',
                'exercise_type': 'multiple_choice',
                'theory': 'Theory 1',
                'exercise_introduction': 'Intro 1',
                'exercise_input': 'Input 1',
                'expected_output': 'Output 1',
                'topic': 'Daily Life'
            },
            {
                'source_lang': 'es',
                'target_lang': 'en',
                'difficulty_level': 'B1',
                'exercise_type': 'fill_blank',
                'theory': 'Theory 2',
                'exercise_introduction': 'Intro 2',
                'exercise_input': 'Input 2',
                'expected_output': 'Output 2',
                'topic': 'Food & Dining'
            }
        ]
        
        combo_ids = ["COMBO_001", "COMBO_004"]
        
        # Bulk save
        saved_count = repo.bulk_save_exercises(exercises_data, combo_ids)
        assert saved_count == 2
        
        # Verify retrieval
        exercises = repo.get_exercises_by_criteria(source_lang='es', target_lang='en')
        assert len(exercises) == 2
        
        # Verify statistics
        stats = repo.get_exercise_statistics()
        assert stats['total_exercises'] == 2
        assert 'multiple_choice' in stats['type_breakdown']
        assert 'fill_blank' in stats['type_breakdown']

class TestErrorHandlingIntegration:
    """Integration tests for error handling and recovery."""
    
    @pytest.fixture
    def error_database(self):
        """Create database for error testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        from scripts.init_curriculum_database import init_curriculum_database
        init_curriculum_database(f"sqlite:///{path}")
        
        yield f"sqlite:///{path}"
        
        if os.path.exists(path):
            os.unlink(path)
    
    def test_schema_not_found_error(self, error_database):
        """Test handling of missing schema error."""
        orchestrator = ContentOrchestrator(error_database)
        
        # Try to get schema for non-existent exercise type
        with pytest.raises(ValueError, match="No schema found"):
            orchestrator.get_schema_for_exercise_type(ExerciseTypeID.MULTIPLE_CHOICE)
    
    def test_database_connection_error(self):
        """Test handling of database connection errors."""
        # Test with invalid database URL
        with pytest.raises(Exception):
            parser = CurriculumStructureParser("sqlite:///nonexistent/path/db.db")
            parser.parse_curriculum_from_database()
    
    @patch('orchestrator.content_orchestrator.SchemaAwareGenerator')
    def test_generation_failure_handling(self, mock_generator_class, error_database):
        """Test handling of generation failures."""
        # Mock generator that fails
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Test generation failure"
        mock_generator.generate_with_schema.return_value = mock_result
        
        # Initialize database
        orchestrator = ContentOrchestrator(error_database)
        orchestrator.llm_generator = mock_generator
        
        # Run generation with failure
        results = orchestrator.orchestrate_content_generation(batch_size=1, variations_per_combo=2)
        
        # Verify failure handling
        assert results.successful == 0
        assert results.failed == 2
        assert len(results.errors) == 2
        assert "Test generation failure" in str(results.errors)

class TestEndToEndPipelineIntegration:
    """End-to-end integration tests for the complete pipeline."""
    
    @pytest.fixture
    def complete_pipeline(self):
        """Setup complete pipeline with mocked LLM."""
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
        
        # Create orchestrator with mocked LLM
        orchestrator = ContentOrchestrator(f"sqlite:///{path}")
        
        # Mock LLM generator
        mock_generator = Mock(spec=SchemaAwareGenerator)
        mock_result = Mock()
        mock_result.success = True
        mock_result.theory = "E2E test theory"
        mock_result.exercise_introduction = "E2E test introduction"
        mock_result.exercise_input = "E2E test input"
        mock_result.expected_output = "E2E test output"
        mock_generator.generate_with_schema.return_value = mock_result
        
        orchestrator.llm_generator = mock_generator
        
        yield orchestrator
        
        if os.path.exists(path):
            os.unlink(path)
    
    def test_complete_pipeline_success(self, complete_pipeline):
        """Test complete successful pipeline execution."""
        # Run pipeline
        results = complete_pipeline.orchestrate_content_generation(
            batch_size=3, 
            variations_per_combo=2
        )
        
        # Verify results
        assert results.total_requested == 6  # 3 combos × 2 variations
        assert results.successful == 6
        assert results.failed == 0
        assert len(results.exercises) == 6
        assert len(results.errors) == 0
        
        # Verify exercises saved
        stats = complete_pipeline.exercise_repo.get_exercise_statistics()
        assert stats['total_exercises'] == 6
        
        # Verify LLM called correctly
        assert complete_pipeline.llm_generator.generate_with_schema.call_count == 6
    
    def test_pipeline_status_tracking(self, complete_pipeline):
        """Test pipeline status tracking integration."""
        # Get initial stats
        initial_stats = complete_pipeline.get_generation_statistics()
        assert initial_stats['pending'] == 54
        assert initial_stats['completed'] == 0
        
        # Run pipeline
        results = complete_pipeline.orchestrate_content_generation(
            batch_size=2, 
            variations_per_combo=1
        )
        
        # Verify status updates
        final_stats = complete_pipeline.get_generation_statistics()
        assert final_stats['pending'] == 52  # 54 - 2 completed
        assert final_stats['completed'] == 2
    
    def test_pipeline_variation_tracking(self, complete_pipeline):
        """Test pipeline variation generation tracking."""
        results = complete_pipeline.orchestrate_content_generation(
            batch_size=1, 
            variations_per_combo=5
        )
        
        # Verify variation tracking
        assert results.total_requested == 5
        assert len(results.exercises) == 5
        
        # Verify different exercise IDs for variations
        exercise_ids = [ex.curriculum_combo_id for ex in results.exercises]
        assert len(set(exercise_ids)) == 1  # Same base combo
        assert all("-v" in combo_id for combo_id in exercise_ids)  # All have variation suffix

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
