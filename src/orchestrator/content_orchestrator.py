"""Content Generation Orchestrator

This module orchestrates the curriculum content generation pipeline by:
1. Querying pending curriculum combinations
2. Retrieving exercise schemas for each combination
3. Coordinating with LLM generators
4. Managing generation status and progress

Key Functions:
- orchestrate_content_generation() -> GenerationResults
- generate_batch_of_exercises() -> List[Exercise]
- get_schema_for_combination() -> ExerciseSchema
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services.curriculum.parser import CurriculumStructureParser, GenerationSpec
from services.curriculum.curriculum_database import ExerciseTypeID
from services.llm.schema_aware_generator import SchemaAwareGenerator
from services.validation.exercise_evaluator import ExerciseEvaluator, EvaluationScore
from data.repositories.exercise_repo import ExerciseRepository, save_exercise_from_orchestrator

logger = logging.getLogger(__name__)

@dataclass
class ExerciseSchema:
    """Exercise schema from database."""
    id: str
    exercise_type: str
    field_theory_description: str
    field_introduction_description: str
    field_input_description: str
    field_input_format: str
    field_output_description: str
    field_output_format: str
    validation_rules: str
    example_theory: str
    example_introduction: str
    example_input: str
    example_output: str

@dataclass
class GeneratedExercise:
    """Generated exercise data."""
    curriculum_combo_id: str
    exercise_type_id: str
    theory: str
    exercise_introduction: str
    exercise_input: str
    expected_output: str
    source_lang: str
    target_lang: str
    difficulty_level: str
    topic: str
    generated_at: datetime

@dataclass
class GenerationResults:
    """Results of content generation batch."""
    total_requested: int
    total_generated: int
    successful: int
    failed: int
    exercises: List[GeneratedExercise]
    errors: List[str]
    start_time: datetime
    end_time: datetime

class ContentOrchestrator:
    """Orchestrates curriculum content generation pipeline."""
    
    def __init__(self, database_url: str = "sqlite:///scripts/curriculum.db"):
        """Initialize the orchestrator with database connections."""
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.curriculum_parser = CurriculumStructureParser(database_url)
        self.llm_generator = SchemaAwareGenerator()
        self.exercise_evaluator = ExerciseEvaluator()
        self.exercise_repo = ExerciseRepository(database_url)
        
        # Ensure exercises table exists
        self.exercise_repo.create_exercises_table()
        
    def orchestrate_content_generation(self, batch_size: int = 10, variations_per_combo: int = 10) -> GenerationResults:
        """Main orchestrator for curriculum generation pipeline.
        
        Args:
            batch_size: Number of curriculum combinations to process
            variations_per_combo: Number of exercise variations to generate per combination
            
        Returns:
            GenerationResults with success metrics and generated exercises
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting content generation batch (size: {batch_size}, variations: {variations_per_combo})")
        
        # Get pending curriculum combinations
        pending_specs = self.curriculum_parser.get_pending_combinations(limit=batch_size)
        
        if not pending_specs:
            logger.info("No pending curriculum combinations found")
            return GenerationResults(
                total_requested=0,
                total_generated=0,
                successful=0,
                failed=0,
                exercises=[],
                errors=["No pending combinations found"],
                start_time=start_time,
                end_time=datetime.utcnow()
            )
        
        # Generate exercises for each combination with variations
        exercises = []
        errors = []
        successful = 0
        failed = 0
        total_exercises_to_generate = len(pending_specs) * variations_per_combo
        current_exercise_count = 0
        
        logger.info(f"Starting generation: {total_exercises_to_generate} total exercises to generate")
        
        for spec_idx, spec in enumerate(pending_specs):
            try:
                # Get schema for this exercise type
                schema = self.get_schema_for_exercise_type(spec.exercise_type_id)
                
                # Mark as in-progress
                self.curriculum_parser.update_generation_status(spec.id, "in_progress")
                
                logger.info(f"Processing {spec_idx+1}/{len(pending_specs)}: {spec.id} - {spec.category} | {spec.exercise_type} | {spec.topic}")
                
                # Generate multiple variations for this combination
                combo_accepted = 0
                combo_failed = 0
                
                for variation_num in range(variations_per_combo):
                    current_exercise_count += 1
                    
                    # Show countdown progress
                    progress_pct = (current_exercise_count / total_exercises_to_generate) * 100
                    logger.info(f"🎯 Exercise {current_exercise_count}/{total_exercises_to_generate} ({progress_pct:.1f}%) - {spec.id}-v{variation_num}")
                    
                    try:
                        # Generate exercise with variation seed
                        exercise = self.generate_exercise_with_context(
                            spec, schema, variation_num=variation_num
                        )
                        
                        if exercise:
                            # Store immediately in database
                            exercise_id = save_exercise_from_orchestrator(
                                exercise, f"{spec.id}-v{variation_num}"
                            )
                            
                            if exercise_id:
                                exercises.append(exercise)
                                successful += 1
                                combo_accepted += 1
                                logger.info(f"✅ Saved exercise {exercise_id} (accepted)")
                            else:
                                failed += 1
                                combo_failed += 1
                                logger.error(f"❌ Failed to save exercise {spec.id}-v{variation_num}")
                        else:
                            failed += 1
                            combo_failed += 1
                            logger.warning(f"❌ Exercise {spec.id}-v{variation_num} rejected by evaluator")
                            
                    except Exception as e:
                        failed += 1
                        combo_failed += 1
                        error_msg = f"Error generating {spec.id}-v{variation_num}: {e}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                
                # Update combination status based on results
                if combo_accepted > 0:
                    self.curriculum_parser.update_generation_status(
                        spec.id, "completed", combo_accepted
                    )
                    logger.info(f"📊 {spec.id}: {combo_accepted}/{variations_per_combo} exercises accepted")
                else:
                    self.curriculum_parser.update_generation_status(
                        spec.id, "failed", 0
                    )
                    logger.error(f"❌ {spec.id}: All {variations_per_combo} exercises failed")
                
                # Show batch progress summary
                batch_progress = ((spec_idx + 1) / len(pending_specs)) * 100
                logger.info(f"🔄 Batch progress: {spec_idx+1}/{len(pending_specs)} ({batch_progress:.1f}%) - Total accepted: {successful}")
                
            except Exception as e:
                failed += variations_per_combo  # Count all variations as failed
                error_msg = f"Error processing {spec.id}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                self.curriculum_parser.update_generation_status(spec.id, "failed", 0)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Generation completed: {successful} successful, {failed} failed, {duration:.2f}s")
        
        return GenerationResults(
            total_requested=len(pending_specs) * variations_per_combo,
            total_generated=len(exercises),
            successful=successful,
            failed=failed,
            exercises=exercises,
            errors=errors,
            start_time=start_time,
            end_time=end_time
        )
    
    def get_schema_for_exercise_type(self, exercise_type_id: ExerciseTypeID) -> ExerciseSchema:
        """Retrieve exercise schema from database.
        
        Args:
            exercise_type_id: Standardized exercise type ID
            
        Returns:
            ExerciseSchema with field specifications
        """
        session = self.SessionLocal()
        try:
            result = session.execute(text("""
                SELECT id, exercise_type, field_theory_description, field_introduction_description,
                       field_input_description, field_input_format, field_output_description, field_output_format,
                       validation_rules, example_theory, example_introduction, example_input, example_output
                FROM exercise_schemas
                WHERE id = :exercise_type_id AND is_active = TRUE
            """), {'exercise_type_id': exercise_type_id.value})
            
            row = result.fetchone()
            
            if not row:
                raise ValueError(f"No schema found for exercise type: {exercise_type_id.value}")
            
            return ExerciseSchema(
                id=row.id,
                exercise_type=row.exercise_type,
                field_theory_description=row.field_theory_description,
                field_introduction_description=row.field_introduction_description,
                field_input_description=row.field_input_description,
                field_input_format=row.field_input_format,
                field_output_description=row.field_output_description,
                field_output_format=row.field_output_format,
                validation_rules=row.validation_rules,
                example_theory=row.example_theory,
                example_introduction=row.example_introduction,
                example_input=row.example_input,
                example_output=row.example_output
            )
            
        except Exception as e:
            logger.error(f"Error retrieving schema for {exercise_type_id}: {e}")
            raise
        finally:
            session.close()
    
    def generate_exercise_with_context(self, spec: GenerationSpec, schema: ExerciseSchema, variation_num: int = 0) -> Optional[GeneratedExercise]:
        """Generate single exercise with schema-specific context and evaluation.
        
        Args:
            spec: Generation specification from curriculum
            schema: Exercise schema with field requirements
            variation_num: Variation number for generating multiple exercises per combo
            
        Returns:
            GeneratedExercise or None if generation failed or evaluation rejected
        """
        try:
            # Step 1: Generate exercise using LLM
            generation_result = self.llm_generator.generate_with_schema(
                spec, schema, variation_num=variation_num
            )
            
            if not generation_result.success:
                logger.error(f"LLM generation failed for {spec.id}: {generation_result.error_message}")
                return None
            
            # Step 2: Create exercise data for evaluation
            exercise_data = {
                'theory': generation_result.theory,
                'exercise_introduction': generation_result.exercise_introduction,
                'exercise_input': generation_result.exercise_input,
                'expected_output': generation_result.expected_output
            }
            
            # Step 3: Evaluate exercise using LLM judge
            exercise_spec = {
                'language_pair_name': spec.language_pair_name,
                'level': spec.level,
                'category': spec.category,
                'exercise_type': spec.exercise_type,
                'topic': spec.topic
            }
            
            schema_spec = {
                'field_theory_description': schema.field_theory_description,
                'field_introduction_description': schema.field_introduction_description,
                'field_input_description': schema.field_input_description,
                'field_output_description': schema.field_output_description
            }
            
            evaluation = self.exercise_evaluator.evaluate_exercise(
                exercise_data, exercise_spec, schema_spec, variation_num
            )
            
            # Step 4: Check if exercise meets quality standards
            if not evaluation.is_acceptable():
                logger.warning(f"Exercise {spec.id}-v{variation_num} rejected: {evaluation.result.value}")
                logger.debug(f"Evaluation feedback: {evaluation.feedback}")
                return None
            
            logger.info(f"Exercise {spec.id}-v{variation_num} accepted: {evaluation.result.value} (score: {evaluation.overall_score:.2f})")
            
            # Step 5: Create GeneratedExercise object with evaluation data
            exercise = GeneratedExercise(
                curriculum_combo_id=spec.id,
                exercise_type_id=spec.exercise_type_id.value,
                theory=generation_result.theory,
                exercise_introduction=generation_result.exercise_introduction,
                exercise_input=generation_result.exercise_input,
                expected_output=generation_result.expected_output,
                source_lang=spec.language_pair[0],
                target_lang=spec.language_pair[1],
                difficulty_level=spec.level,
                topic=spec.topic,
                generated_at=datetime.utcnow()
            )
            
            # Log evaluation summary (database save happens in main loop)
            logger.info(f"Exercise {spec.id}-v{variation_num} accepted: {evaluation.result.value} (score: {evaluation.overall_score:.2f})")
            
            return exercise
            
        except Exception as e:
            logger.error(f"Error generating exercise for {spec.id}: {e}")
            return None
    
    def get_generation_statistics(self) -> Dict:
        """Get comprehensive generation statistics.
        
        Returns:
            Dictionary with generation statistics
        """
        return self.curriculum_parser.get_generation_statistics()
    
    def get_pending_count(self) -> int:
        """Get count of pending curriculum combinations.
        
        Returns:
            Number of pending combinations
        """
        session = self.SessionLocal()
        try:
            result = session.execute(text("""
                SELECT COUNT(*) FROM curriculum_structure WHERE generation_status = 'pending'
            """))
            return result.fetchone()[0]
        finally:
            session.close()
    
    def preview_next_batch(self, batch_size: int = 5) -> List[Dict]:
        """Preview what will be generated in the next batch.
        
        Args:
            batch_size: Number of combinations to preview
            
        Returns:
            List of combination details
        """
        pending_specs = self.curriculum_parser.get_pending_combinations(limit=batch_size)
        
        preview = []
        for spec in pending_specs:
            preview.append({
                'id': spec.id,
                'language_pair': spec.language_pair_name,
                'level': spec.level,
                'category': spec.category,
                'exercise_type': spec.exercise_type,
                'topic': spec.topic,
                'priority': spec.priority
            })
        
        return preview

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def run_content_generation_batch(batch_size: int = 10) -> GenerationResults:
    """Run a content generation batch.
    
    Args:
        batch_size: Number of exercises to generate
        
    Returns:
        GenerationResults with batch statistics
    """
    orchestrator = ContentOrchestrator()
    return orchestrator.orchestrate_content_generation(batch_size)

def get_generation_queue_info() -> Dict:
    """Get information about the generation queue.
    
    Returns:
        Dictionary with queue statistics
    """
    orchestrator = ContentOrchestrator()
    stats = orchestrator.get_generation_statistics()
    pending_count = orchestrator.get_pending_count()
    
    return {
        'pending_count': pending_count,
        'total_combinations': stats['total_combinations'],
        'completed_count': stats['completed'],
        'failed_count': stats['failed'],
        'completion_rate': stats['completion_rate']
    }

if __name__ == "__main__":
    # Demo the orchestrator
    logging.basicConfig(level=logging.INFO)
    
    print("🎓 CONTENT ORCHESTRATOR DEMO")
    print("=" * 60)
    
    orchestrator = ContentOrchestrator()
    
    # Show queue info
    queue_info = get_generation_queue_info()
    print(f"📊 Generation Queue:")
    print(f"   Pending: {queue_info['pending_count']}")
    print(f"   Completed: {queue_info['completed_count']}")
    print(f"   Failed: {queue_info['failed_count']}")
    print(f"   Completion Rate: {queue_info['completion_rate']:.1f}%")
    
    # Preview next batch
    preview = orchestrator.preview_next_batch(3)
    print(f"\n🔍 Next Batch Preview:")
    for item in preview:
        print(f"   {item['id']}: {item['language_pair']} | {item['category']} | {item['exercise_type']}")
    
    # Test schema retrieval
    from services.curriculum.curriculum_database import ExerciseTypeID
    try:
        schema = orchestrator.get_schema_for_exercise_type(ExerciseTypeID.MULTIPLE_CHOICE)
        print(f"\n📋 Sample Schema ({schema.exercise_type}):")
        print(f"   Theory: {schema.field_theory_description}")
        print(f"   Input Format: {schema.field_input_format}")
        print(f"   Output Format: {schema.field_output_format}")
    except Exception as e:
        print(f"❌ Schema retrieval failed: {e}")
    
    print("\n✅ Orchestrator demo completed!")
