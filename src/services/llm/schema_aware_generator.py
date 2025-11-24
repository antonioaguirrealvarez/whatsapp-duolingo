"""Schema-Aware Content Generator

This module generates exercise content using LLMs with schema-specific prompts
and validation. It integrates with the content orchestrator to produce
structured exercises that match the 4-field schema requirements.

Key Functions:
- generate_with_schema() -> dict
- build_context_aware_prompt() -> str
- validate_llm_output() -> bool
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from services.llm.gateway import LLMGateway
from ..curriculum.curriculum_database import ExerciseTypeID

logger = logging.getLogger(__name__)

@dataclass
class GenerationResult:
    """Result of LLM content generation."""
    success: bool
    theory: Optional[str] = None
    exercise_introduction: Optional[str] = None
    exercise_input: Optional[str] = None
    expected_output: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0

class SchemaAwareGenerator:
    """Generates exercise content with schema-specific prompts and validation."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """Initialize the generator with LLM configuration."""
        self.llm_gateway = LLMGateway()
        self.model_name = model_name
        self.json_parser = JsonOutputParser()
        
    def generate_with_schema(self, generation_spec, exercise_schema, variation_num: int = 0) -> GenerationResult:
        """Generate exercise content with schema-specific context.
        
        Args:
            generation_spec: GenerationSpec from curriculum parser
            exercise_schema: ExerciseSchema from database
            variation_num: Variation number for generating different exercises
            
        Returns:
            GenerationResult with structured exercise data
        """
        try:
            # Build context-aware prompt with variation seed
            prompt = self.build_context_aware_prompt(generation_spec, exercise_schema, variation_num)
            
            # Generate content with LLM
            response = self.llm_gateway.invoke(prompt, model_type='fast')
            
            # Parse and validate response
            exercise_data = self._parse_llm_response(response)
            
            # Validate against schema
            if self._validate_exercise_data(exercise_data, exercise_schema):
                return GenerationResult(
                    success=True,
                    theory=exercise_data.get('theory'),
                    exercise_introduction=exercise_data.get('exercise_introduction'),
                    exercise_input=exercise_data.get('exercise_input'),
                    expected_output=exercise_data.get('expected_output')
                )
            else:
                return GenerationResult(
                    success=False,
                    error_message="Generated content failed schema validation"
                )
                
        except Exception as e:
            logger.error(f"Error generating exercise: {e}")
            return GenerationResult(
                success=False,
                error_message=str(e)
            )
    
    def build_context_aware_prompt(self, generation_spec, exercise_schema, variation_num: int = 0) -> str:
        """Build context-aware prompt for LLM generation.
        
        Args:
            generation_spec: GenerationSpec with curriculum context
            exercise_schema: ExerciseSchema with field requirements
            variation_num: Variation number for generating different exercises
            
        Returns:
            Complete prompt for LLM generation
        """
        # Add variation seed to ensure different outputs
        variation_context = f"\nVARIATION SEED: {variation_num}\nGenerate a completely different exercise than previous variations."
        # Base system message
        system_message = f"""
You are an expert language learning content creator. Generate educational exercises for language learners.

Generate 1 exercise for the following specifications:
- Source Language: {generation_spec.language_pair[0]}
- Target Language: {generation_spec.language_pair[1]}
- Difficulty Level: {generation_spec.level} (CEFR)
- Exercise Type: {generation_spec.exercise_type}
- Topic: {generation_spec.topic}
- Content Category: {generation_spec.category}

Exercise Type: {exercise_schema.exercise_type}
- Theory Description: {exercise_schema.field_theory_description}
- Input Format: {exercise_schema.field_input_format}
- Output Format: {exercise_schema.field_output_format}
- Validation Rules: {exercise_schema.validation_rules}

Requirements:
- Content must be appropriate for {generation_spec.level} level learners
- Content should be culturally relevant for {generation_spec.language_pair[0]} speakers
- Follow the exact format specified for each field
- Ensure all fields are complete and accurate

Output format: JSON object with the following fields:
{{
    "theory": "Educational content explaining concepts, vocabulary, or grammar rules with examples",
    "exercise_introduction": "Clear instructions for the user explaining the exercise format and what they need to do",
    "exercise_input": "The actual exercise content following the specified format",
    "expected_output": "The correct answer or expected response from the user"
}}

Example for reference:
- Theory: {exercise_schema.example_theory}
- Introduction: {exercise_schema.example_introduction}
- Input: {exercise_schema.example_input}
- Output: {exercise_schema.example_output}

Generate exactly 1 exercise following these specifications:
{variation_context}
"""
        
        return system_message.strip()
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured data.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed exercise data dictionary
        """
        try:
            # Try to parse as JSON first
            if response.strip().startswith('{'):
                import json
                return json.loads(response)
            
            # If not JSON, try to extract fields manually
            return self._extract_fields_from_text(response)
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {}
    
    def _extract_fields_from_text(self, response: str) -> Dict:
        """Extract fields from text response when JSON parsing fails.
        
        Args:
            response: Text response from LLM
            
        Returns:
            Dictionary with extracted fields
        """
        fields = {
            'theory': '',
            'exercise_introduction': '',
            'exercise_input': '',
            'expected_output': ''
        }
        
        # Simple field extraction (can be enhanced)
        lines = response.split('\n')
        current_field = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect field headers
            if 'theory' in line.lower() and ':' in line:
                current_field = 'theory'
                fields[current_field] = line.split(':', 1)[1].strip()
            elif 'introduction' in line.lower() and ':' in line:
                current_field = 'exercise_introduction'
                fields[current_field] = line.split(':', 1)[1].strip()
            elif 'input' in line.lower() and ':' in line:
                current_field = 'exercise_input'
                fields[current_field] = line.split(':', 1)[1].strip()
            elif 'output' in line.lower() and ':' in line:
                current_field = 'expected_output'
                fields[current_field] = line.split(':', 1)[1].strip()
            elif current_field and line:
                # Continue current field content
                fields[current_field] += ' ' + line
        
        return fields
    
    def _validate_exercise_data(self, exercise_data: Dict, exercise_schema) -> bool:
        """Validate exercise data against schema requirements.
        
        Args:
            exercise_data: Generated exercise data
            exercise_schema: Schema requirements
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['theory', 'exercise_introduction', 'exercise_input', 'expected_output']
        
        # Check all required fields are present
        for field in required_fields:
            if field not in exercise_data or not exercise_data[field]:
                logger.error(f"Missing or empty field: {field}")
                return False
        
        # Validate field lengths (basic validation)
        theory = exercise_data['theory']
        if len(theory) < 50 or len(theory) > 2000:
            logger.error(f"Theory field length invalid: {len(theory)} chars")
            return False
        
        introduction = exercise_data['exercise_introduction']
        if len(introduction) < 10 or len(introduction) > 500:
            logger.error(f"Introduction field length invalid: {len(introduction)} chars")
            return False
        
        input_field = exercise_data['exercise_input']
        if len(input_field) < 10 or len(input_field) > 1000:
            logger.error(f"Input field length invalid: {len(input_field)} chars")
            return False
        
        output = exercise_data['expected_output']
        if len(output) < 1 or len(output) > 500:
            logger.error(f"Output field length invalid: {len(output)} chars")
            return False
        
        return True
    
    def generate_batch_with_retry(self, specs_and_schemas: List[tuple], max_retries: int = 2) -> List[GenerationResult]:
        """Generate batch of exercises with retry logic.
        
        Args:
            specs_and_schemas: List of (generation_spec, exercise_schema) tuples
            max_retries: Maximum number of retries per exercise
            
        Returns:
            List of GenerationResult objects
        """
        results = []
        
        for generation_spec, exercise_schema in specs_and_schemas:
            retry_count = 0
            result = None
            
            while retry_count <= max_retries:
                result = self.generate_with_schema(generation_spec, exercise_schema)
                
                if result.success:
                    break
                    
                retry_count += 1
                logger.warning(f"Retry {retry_count} for {generation_spec.id}")
            
            if result:
                result.retry_count = retry_count
                results.append(result)
        
        return results

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def generate_exercise_for_spec(generation_spec, exercise_schema) -> GenerationResult:
    """Generate exercise for a single specification.
    
    Args:
        generation_spec: GenerationSpec from curriculum parser
        exercise_schema: ExerciseSchema from database
        
    Returns:
        GenerationResult with generated exercise data
    """
    generator = SchemaAwareGenerator()
    return generator.generate_with_schema(generation_spec, exercise_schema)

if __name__ == "__main__":
    # Demo the schema-aware generator
    logging.basicConfig(level=logging.INFO)
    
    print("🎓 SCHEMA-AWARE GENERATOR DEMO")
    print("=" * 60)
    
    # This would normally use real specs and schemas
    print("🔧 Schema-aware generator initialized")
    print("📝 Ready to generate exercises with 4-field structure")
    print("✅ Generator demo completed!")
