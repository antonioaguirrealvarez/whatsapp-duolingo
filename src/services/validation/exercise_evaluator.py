"""Exercise Evaluator using LLM Judge

This module provides comprehensive exercise evaluation using an LLM judge
to validate both content correctness and schema compliance before storage.

Features:
- Content validation: Language accuracy, educational appropriateness
- Schema validation: 4-field structure compliance
- Quality scoring: Multi-criteria evaluation
- Detailed feedback: Specific improvement suggestions
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..llm.gateway import LLMGateway
from core.config import get_settings
from core.exceptions import LLMError

logger = logging.getLogger(__name__)

class ValidationResult(Enum):
    """Evaluation result status."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_IMPROVEMENT = "needs_improvement"
    REJECTED = "rejected"

@dataclass
class EvaluationScore:
    """Detailed evaluation scoring."""
    overall_score: float  # 0.0 to 1.0
    content_score: float  # Language accuracy, educational value
    schema_score: float   # Structure compliance
    quality_score: float  # Overall exercise quality
    result: ValidationResult
    feedback: str
    suggestions: list[str]
    
    def is_acceptable(self) -> bool:
        """Check if exercise meets minimum quality standards."""
        return self.result in [ValidationResult.EXCELLENT, ValidationResult.GOOD, ValidationResult.ACCEPTABLE]

class ExerciseEvaluator:
    """LLM-based exercise evaluator for content and schema validation."""
    
    def __init__(self):
        """Initialize the evaluator with LLM gateway."""
        self.settings = get_settings()
        self.llm_gateway = LLMGateway()
        logger.info("Exercise evaluator initialized")
    
    def evaluate_exercise(
        self,
        exercise_data: Dict[str, Any],
        exercise_spec: Dict[str, Any],
        schema_spec: Dict[str, Any],
        variation_num: int = 0
    ) -> EvaluationScore:
        """
        Evaluate exercise using LLM judge.
        
        Args:
            exercise_data: Generated exercise content
            exercise_spec: Curriculum specification (language, level, type, topic)
            schema_spec: Exercise schema requirements
            variation_num: Variation number for context
            
        Returns:
            EvaluationScore with detailed feedback
        """
        try:
            # Build evaluation prompt
            prompt = self._build_evaluation_prompt(
                exercise_data, exercise_spec, schema_spec, variation_num
            )
            
            # Get evaluation from LLM (use fast model for evaluation)
            evaluation_response = self.llm_gateway.invoke(
                prompt=prompt,
                model_type="fast"  # Use fast model for evaluation
            )
            
            # Parse evaluation response
            evaluation = self._parse_evaluation_response(evaluation_response)
            
            logger.info(f"Evaluation completed: {evaluation.result.value} (score: {evaluation.overall_score:.2f})")
            return evaluation
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            # Return conservative evaluation on failure
            return EvaluationScore(
                overall_score=0.0,
                content_score=0.0,
                schema_score=0.0,
                quality_score=0.0,
                result=ValidationResult.REJECTED,
                feedback=f"Evaluation system error: {str(e)}",
                suggestions=["Regenerate exercise", "Check LLM availability"]
            )
    
    def _build_evaluation_prompt(
        self,
        exercise_data: Dict[str, Any],
        exercise_spec: Dict[str, Any],
        schema_spec: Dict[str, Any],
        variation_num: int
    ) -> str:
        """Build comprehensive evaluation prompt for LLM judge."""
        
        prompt = f"""You are an expert language education evaluator. Evaluate the following exercise for correctness and quality.

## EXERCISE SPECIFICATION
- Language Pair: {exercise_spec.get('language_pair_name', 'N/A')}
- Level: {exercise_spec.get('level', 'N/A')}
- Category: {exercise_spec.get('category', 'N/A')}
- Exercise Type: {exercise_spec.get('exercise_type', 'N/A')}
- Topic: {exercise_spec.get('topic', 'N/A')}
- Variation Number: {variation_num}

## EXERCISE CONTENT
{self._format_exercise_content(exercise_data)}

## SCHEMA REQUIREMENTS
{self._format_schema_requirements(schema_spec)}

## EVALUATION CRITERIA

### 1. Content Validation (40% weight)
- **Language Accuracy**: Is the Spanish/English content grammatically correct?
- **Educational Appropriateness**: Is the content suitable for {exercise_spec.get('level', 'N/A')} level?
- **Topic Relevance**: Does the exercise match the {exercise_spec.get('topic', 'N/A')} topic?
- **Category Alignment**: Does it fit the {exercise_spec.get('category', 'N/A')} category?

### 2. Schema Validation (30% weight)
- **4-Field Structure**: Does it have all required fields (theory, introduction, input, output)?
- **Field Content**: Is each field properly filled and meaningful?
- **Format Compliance**: Does the input/output match the expected format?

### 3. Quality Assessment (30% weight)
- **Clarity**: Is the exercise clear and understandable?
- **Engagement**: Is it interesting and motivating for learners?
- **Completeness**: Are all components present and well-formed?

## EVALUATION TASK

Provide a detailed evaluation in this exact JSON format:

{{
    "overall_score": 0.0-1.0,
    "content_score": 0.0-1.0,
    "schema_score": 0.0-1.0,
    "quality_score": 0.0-1.0,
    "result": "excellent|good|acceptable|needs_improvement|rejected",
    "feedback": "Detailed explanation of strengths and weaknesses",
    "suggestions": ["Specific improvement suggestion 1", "Specific improvement suggestion 2"]
}}

Scoring Guidelines:
- 0.8-1.0: Excellent - High quality, ready for production
- 0.6-0.79: Good - Minor issues, acceptable for use
- 0.4-0.59: Acceptable - Some issues, usable with improvements
- 0.2-0.39: Needs Improvement - Significant issues, requires regeneration
- 0.0-0.19: Rejected - Major problems, not suitable for use

Evaluate honestly and provide specific, actionable feedback."""
        
        return prompt
    
    def _format_exercise_content(self, exercise_data: Dict[str, Any]) -> str:
        """Format exercise content for evaluation."""
        content = []
        
        field_mapping = {
            'theory': 'Theory/Instruction',
            'exercise_introduction': 'Exercise Introduction',
            'exercise_input': 'Exercise Input/Question',
            'expected_output': 'Expected Output/Answer'
        }
        
        for field, label in field_mapping.items():
            value = exercise_data.get(field, 'MISSING')
            content.append(f"**{label}**: {value}")
        
        return "\n".join(content)
    
    def _format_schema_requirements(self, schema_spec: Dict[str, Any]) -> str:
        """Format schema requirements for evaluation."""
        requirements = []
        
        if hasattr(schema_spec, 'field_theory_description'):
            requirements.append(f"**Theory**: {schema_spec.field_theory_description}")
        if hasattr(schema_spec, 'field_introduction_description'):
            requirements.append(f"**Introduction**: {schema_spec.field_introduction_description}")
        if hasattr(schema_spec, 'field_input_description'):
            requirements.append(f"**Input**: {schema_spec.field_input_description}")
        if hasattr(schema_spec, 'field_output_description'):
            requirements.append(f"**Output**: {schema_spec.field_output_description}")
        
        return "\n".join(requirements) if requirements else "Standard 4-field exercise structure"
    
    def _parse_evaluation_response(self, response: str) -> EvaluationScore:
        """Parse LLM evaluation response into structured score."""
        try:
            import json
            
            # Try to extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Look for JSON object in response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            
            eval_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['overall_score', 'content_score', 'schema_score', 
                             'quality_score', 'result', 'feedback', 'suggestions']
            
            for field in required_fields:
                if field not in eval_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Convert result string to enum
            result_map = {
                'excellent': ValidationResult.EXCELLENT,
                'good': ValidationResult.GOOD,
                'acceptable': ValidationResult.ACCEPTABLE,
                'needs_improvement': ValidationResult.NEEDS_IMPROVEMENT,
                'rejected': ValidationResult.REJECTED
            }
            
            result = result_map.get(eval_data['result'].lower(), ValidationResult.REJECTED)
            
            return EvaluationScore(
                overall_score=float(eval_data['overall_score']),
                content_score=float(eval_data['content_score']),
                schema_score=float(eval_data['schema_score']),
                quality_score=float(eval_data['quality_score']),
                result=result,
                feedback=str(eval_data['feedback']),
                suggestions=list(eval_data['suggestions'])
            )
            
        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            logger.debug(f"Response content: {response}")
            
            # Return conservative evaluation
            return EvaluationScore(
                overall_score=0.3,
                content_score=0.3,
                schema_score=0.3,
                quality_score=0.3,
                result=ValidationResult.NEEDS_IMPROVEMENT,
                feedback=f"Evaluation parsing error: {str(e)}",
                suggestions=["Check evaluation response format", "Regenerate exercise"]
            )
    
    def batch_evaluate(
        self,
        exercises: list[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], int]]
    ) -> list[EvaluationScore]:
        """
        Evaluate multiple exercises in batch.
        
        Args:
            exercises: List of tuples (exercise_data, exercise_spec, schema_spec, variation_num)
            
        Returns:
            List of evaluation scores
        """
        evaluations = []
        
        for i, (exercise_data, exercise_spec, schema_spec, variation_num) in enumerate(exercises):
            logger.info(f"Evaluating exercise {i+1}/{len(exercises)}")
            evaluation = self.evaluate_exercise(
                exercise_data, exercise_spec, schema_spec, variation_num
            )
            evaluations.append(evaluation)
        
        return evaluations
    
    def get_evaluation_summary(self, evaluations: list[EvaluationScore]) -> Dict[str, Any]:
        """Get summary statistics for batch evaluations."""
        if not evaluations:
            return {}
        
        total = len(evaluations)
        acceptable = sum(1 for e in evaluations if e.is_acceptable())
        
        result_counts = {}
        for result in ValidationResult:
            count = sum(1 for e in evaluations if e.result == result)
            result_counts[result.value] = count
        
        avg_scores = {
            'overall': sum(e.overall_score for e in evaluations) / total,
            'content': sum(e.content_score for e in evaluations) / total,
            'schema': sum(e.schema_score for e in evaluations) / total,
            'quality': sum(e.quality_score for e in evaluations) / total
        }
        
        return {
            'total_evaluated': total,
            'acceptable_count': acceptable,
            'acceptance_rate': acceptable / total,
            'result_distribution': result_counts,
            'average_scores': avg_scores
        }
