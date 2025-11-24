"""Unit Tests for Curriculum Generation Pipeline

Tests the individual components of the curriculum generation system:
- Curriculum structure parser
- Exercise schema registry  
- Content orchestrator
- LLM generator
- Exercise repository

Test Structure:
- Unit tests for individual functions
- Integration tests for component interaction
- Mock LLM calls to avoid API costs
- Database transaction rollback
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.curriculum.parser import CurriculumStructureParser, get_mvp_generation_specs
from services.curriculum.curriculum_database import ExerciseTypeID
from orchestrator.content_orchestrator import ContentOrchestrator
from services.llm.schema_aware_generator import SchemaAwareGenerator
from data.repositories.exercise_repo import ExerciseRepository

class TestCurriculumParser:
    """Unit tests for curriculum structure parser."""
    
    def setup_method(self):
        """Setup test database connection."""
        self.parser = CurriculumStructureParser("sqlite:///:memory:")
        # Initialize test database
        from scripts.init_curriculum_database import init_curriculum_database
        init_curriculum_database("sqlite:///:memory:")
    
    def test_parse_curriculum_from_database(self):
        """Test parsing curriculum combinations from database."""
        specs = self.parser.parse_curriculum_from_database()
        
        assert len(specs) == 54
        assert specs[0].id.startswith("COMBO_")
        assert specs[0].language_pair is not None
        assert specs[0].level is not None
        assert specs[0].category is not None
        assert specs[0].exercise_type is not None
        assert specs[0].topic is not None
    
    def test_extract_generation_specs(self):
        """Test extracting generation specifications."""
        specs = self.parser.parse_curriculum_from_database()
        gen_specs = self.parser.extract_generation_specs(specs)
        
        assert len(gen_specs) == len(specs)
        assert gen_specs[0].id == specs[0].id
        assert gen_specs[0].language_pair_name is not None
    
    def test_get_pending_combinations(self):
        """Test retrieving pending combinations."""
        pending = self.parser.get_pending_combinations(limit=5)
        
        assert len(pending) == 5
        assert all(spec.status == 'pending' for spec in pending)
    
    def test_update_generation_status(self):
        """Test updating generation status."""
        specs = self.parser.get_pending_combinations(limit=1)
        spec = specs[0]
        
        success = self.parser.update_generation_status(spec.id, "in_progress")
        assert success is True
        
        # Verify status updated
        updated_specs = self.parser.parse_curriculum_from_database()
        updated_spec = next(s for s in updated_specs if s.id == spec.id)
        assert updated_spec.status == "in_progress"

class TestExerciseSchemaRegistry:
    """Unit tests for exercise schema registry."""
    
    def setup_method(self):
        """Setup test database connection."""
        self.orchestrator = ContentOrchestrator("sqlite:///:memory:")
        # Initialize exercise schemas
        from scripts.init_exercise_schemas import create_exercise_schemas_table, populate_exercise_schemas
        create_exercise_schemas_table(self.orchestrator.engine)
        populate_exercise_schemas(self.orchestrator.SessionLocal())
    
    def test_get_schema_for_exercise_type(self):
        """Test retrieving schema for exercise type."""
        schema = self.orchestrator.get_schema_for_exercise_type(ExerciseTypeID.MULTIPLE_CHOICE)
        
        assert schema is not None
        assert schema.exercise_type == "multiple_choice"
        assert schema.field_theory_description is not None
        assert schema.field_introduction_description is not None
        assert schema.field_input_description is not None
        assert schema.field_output_description is not None
    
    def test_schema_field_requirements(self):
        """Test schema has all required fields."""
        schema = self.orchestrator.get_schema_for_exercise_type(ExerciseTypeID.MULTIPLE_CHOICE)
        
        required_fields = [
            'field_theory_description',
            'field_introduction_description', 
            'field_input_description',
            'field_output_description',
            'validation_rules',
            'example_theory',
            'example_introduction',
            'example_input',
            'example_output'
        ]
        
        for field in required_fields:
            assert hasattr(schema, field)
            assert getattr(schema, field) is not None

class TestContentOrchestrator:
    """Unit tests for content orchestrator."""
    
    def setup_method(self):
        """Setup test orchestrator."""
        self.orchestrator = ContentOrchestrator("sqlite:///:memory:")
        # Initialize database
        from scripts.init_curriculum_database import init_curriculum_database
        from scripts.init_exercise_schemas import create_exercise_schemas_table, populate_exercise_schemas
        init_curriculum_database("sqlite:///:memory:")
        create_exercise_schemas_table(self.orchestrator.engine)
        populate_exercise_schemas(self.orchestrator.SessionLocal())
    
    def test_get_generation_statistics(self):
        """Test retrieving generation statistics."""
        stats = self.orchestrator.get_generation_statistics()
        
        assert 'total_combinations' in stats
        assert 'pending' in stats
        assert 'completed' in stats
        assert 'failed' in stats
        assert 'completion_rate' in stats
        assert stats['total_combinations'] == 54
    
    def test_preview_next_batch(self):
        """Test previewing next batch."""
        preview = self.orchestrator.preview_next_batch(3)
        
        assert len(preview) == 3
        assert all('id' in item for item in preview)
        assert all('language_pair' in item for item in preview)
        assert all('category' in item for item in preview)
    
    @patch('orchestrator.content_orchestrator.SchemaAwareGenerator')
    def test_orchestrate_content_generation_mock(self, mock_generator_class):
        """Test orchestration with mocked LLM generator."""
        # Mock the generator
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        # Mock generation result
        mock_result = Mock()
        mock_result.success = True
        mock_result.theory = "Test theory"
        mock_result.exercise_introduction = "Test introduction"
        mock_result.exercise_input = "Test input"
        mock_result.expected_output = "Test output"
        mock_generator.generate_with_schema.return_value = mock_result
        
        # Create orchestrator with mocked generator
        orchestrator = ContentOrchestrator("sqlite:///:memory:")
        orchestrator.llm_generator = mock_generator
        
        # Initialize database
        from scripts.init_curriculum_database import init_curriculum_database
        from scripts.init_exercise_schemas import create_exercise_schemas_table, populate_exercise_schemas
        init_curriculum_database("sqlite:///:memory:")
        create_exercise_schemas_table(orchestrator.engine)
        populate_exercise_schemas(orchestrator.SessionLocal())
        
        # Run orchestration with small batch
        results = orchestrator.orchestrate_content_generation(batch_size=1, variations_per_combo=2)
        
        assert results.total_requested == 2  # 1 combo × 2 variations
        assert results.successful == 2
        assert results.failed == 0
        assert len(results.exercises) == 2

class TestLLMGenerator:
    """Unit tests for LLM generator."""
    
    def setup_method(self):
        """Setup test generator."""
        self.generator = SchemaAwareGenerator()
    
    @patch('services.llm.schema_aware_generator.LLMGateway')
    def test_build_context_aware_prompt(self, mock_gateway_class):
        """Test building context-aware prompt."""
        # Mock generation spec and schema
        mock_spec = Mock()
        mock_spec.language_pair = ('es', 'en')
        mock_spec.level = 'B1'
        mock_spec.exercise_type = 'multiple_choice'
        mock_spec.topic = 'Daily Life'
        mock_spec.category = 'Vocabulary'
        
        mock_schema = Mock()
        mock_schema.field_theory_description = "Test theory description"
        mock_schema.field_introduction_description = "Test intro description"
        mock_schema.field_input_description = "Test input description"
        mock_schema.field_output_description = "Test output description"
        mock_schema.example_theory = "Example theory"
        mock_schema.example_introduction = "Example intro"
        mock_schema.example_input = "Example input"
        mock_schema.example_output = "Example output"
        
        prompt = self.generator.build_context_aware_prompt(mock_spec, mock_schema, variation_num=1)
        
        assert "VARIATION SEED: 1" in prompt
        assert "Spanish" in prompt
        assert "English" in prompt
        assert "B1" in prompt
        assert "multiple_choice" in prompt
        assert "Daily Life" in prompt
        assert "Vocabulary" in prompt
        assert "completely different exercise" in prompt
    
    def test_parse_llm_response_json(self):
        """Test parsing JSON LLM response."""
        json_response = '{"theory": "Test", "exercise_introduction": "Intro", "exercise_input": "Input", "expected_output": "Output"}'
        
        parsed = self.generator._parse_llm_response(json_response)
        
        assert parsed['theory'] == "Test"
        assert parsed['exercise_introduction'] == "Intro"
        assert parsed['exercise_input'] == "Input"
        assert parsed['expected_output'] == "Output"
    
    def test_validate_exercise_data_success(self):
        """Test successful exercise data validation."""
        exercise_data = {
            'theory': 'This is a test theory that is long enough to pass validation',
            'exercise_introduction': 'This is a test introduction',
            'exercise_input': 'This is test input content',
            'expected_output': 'Expected output'
        }
        
        mock_schema = Mock()
        result = self.generator._validate_exercise_data(exercise_data, mock_schema)
        
        assert result is True
    
    def test_validate_exercise_data_failure(self):
        """Test exercise data validation failure."""
        # Missing required field
        exercise_data = {
            'theory': 'This is a test theory',
            'exercise_introduction': 'This is a test introduction',
            # Missing exercise_input and expected_output
        }
        
        mock_schema = Mock()
        result = self.generator._validate_exercise_data(exercise_data, mock_schema)
        
        assert result is False

class TestExerciseRepository:
    """Unit tests for exercise repository."""
    
    def setup_method(self):
        """Setup test repository."""
        self.repo = ExerciseRepository("sqlite:///:memory:")
        self.repo.create_exercises_table()
    
    def test_create_exercises_table(self):
        """Test exercises table creation."""
        # Should not raise exception
        self.repo.create_exercises_table()
        
        # Check table exists by querying it
        stats = self.repo.get_exercise_statistics()
        assert stats['total_exercises'] == 0
    
    def test_save_generated_exercise(self):
        """Test saving generated exercise."""
        exercise_data = {
            'source_lang': 'es',
            'target_lang': 'en',
            'difficulty_level': 'B1',
            'exercise_type': 'multiple_choice',
            'theory': 'Test theory',
            'exercise_introduction': 'Test introduction',
            'exercise_input': 'Test input',
            'expected_output': 'Test output',
            'topic': 'Daily Life'
        }
        
        exercise_id = self.repo.save_generated_exercise(exercise_data, "COMBO_001")
        
        assert exercise_id is not None
        assert exercise_id.startswith("EX_COMBO_001")
        
        # Verify exercise was saved
        stats = self.repo.get_exercise_statistics()
        assert stats['total_exercises'] == 1
    
    def test_get_exercises_by_criteria(self):
        """Test retrieving exercises by criteria."""
        # Save a test exercise first
        exercise_data = {
            'source_lang': 'es',
            'target_lang': 'en',
            'difficulty_level': 'B1',
            'exercise_type': 'multiple_choice',
            'theory': 'Test theory',
            'exercise_introduction': 'Test introduction',
            'exercise_input': 'Test input',
            'expected_output': 'Test output',
            'topic': 'Daily Life'
        }
        self.repo.save_generated_exercise(exercise_data, "COMBO_001")
        
        # Retrieve by criteria
        exercises = self.repo.get_exercises_by_criteria(
            source_lang='es',
            target_lang='en',
            difficulty_level='B1',
            exercise_type='multiple_choice'
        )
        
        assert len(exercises) == 1
        assert exercises[0].source_lang == 'es'
        assert exercises[0].target_lang == 'en'
        assert exercises[0].difficulty_level == 'B1'
        assert exercises[0].exercise_type == 'multiple_choice'
    
    def test_get_exercise_statistics(self):
        """Test retrieving exercise statistics."""
        stats = self.repo.get_exercise_statistics()
        
        assert 'total_exercises' in stats
        assert 'source_languages' in stats
        assert 'target_languages' in stats
        assert 'difficulty_levels' in stats
        assert 'exercise_types' in stats
        assert 'type_breakdown' in stats

class TestIntegration:
    """Integration tests for curriculum generation pipeline."""
    
    def setup_method(self):
        """Setup integration test environment."""
        self.orchestrator = ContentOrchestrator("sqlite:///:memory:")
        
        # Initialize complete database
        from scripts.init_curriculum_database import init_curriculum_database
        from scripts.init_exercise_schemas import create_exercise_schemas_table, populate_exercise_schemas
        init_curriculum_database("sqlite:///:memory:")
        create_exercise_schemas_table(self.orchestrator.engine)
        populate_exercise_schemas(self.orchestrator.SessionLocal())
    
    @patch('orchestrator.content_orchestrator.SchemaAwareGenerator')
    def test_full_pipeline_integration_mock(self, mock_generator_class):
        """Test full pipeline integration with mocked LLM."""
        # Mock the LLM generator
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        # Mock successful generation
        mock_result = Mock()
        mock_result.success = True
        mock_result.theory = "Integration test theory"
        mock_result.exercise_introduction = "Integration test introduction"
        mock_result.exercise_input = "Integration test input"
        mock_result.expected_output = "Integration test output"
        mock_generator.generate_with_schema.return_value = mock_result
        
        # Replace generator in orchestrator
        self.orchestrator.llm_generator = mock_generator
        
        # Run full pipeline
        results = self.orchestrator.orchestrate_content_generation(
            batch_size=2, 
            variations_per_combo=3
        )
        
        # Verify results
        assert results.total_requested == 6  # 2 combos × 3 variations
        assert results.successful == 6
        assert results.failed == 0
        assert len(results.exercises) == 6
        
        # Verify LLM was called correctly
        assert mock_generator.generate_with_schema.call_count == 6
        
        # Verify exercises were saved
        stats = self.orchestrator.exercise_repo.get_exercise_statistics()
        assert stats['total_exercises'] == 6
    
    def test_mvp_generation_specs(self):
        """Test MVP generation specs function."""
        specs = get_mvp_generation_specs()
        
        assert len(specs) == 54
        
        # Verify language distribution
        lang_distribution = {}
        for spec in specs:
            lang_pair = spec.language_pair_name
            lang_distribution[lang_pair] = lang_distribution.get(lang_pair, 0) + 1
        
        assert 'Spanish → English' in lang_distribution
        assert 'Portuguese → English' in lang_distribution
        assert lang_distribution['Spanish → English'] == 27
        assert lang_distribution['Portuguese → English'] == 27

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
