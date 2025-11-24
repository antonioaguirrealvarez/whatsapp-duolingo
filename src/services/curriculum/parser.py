"""Curriculum Structure Parser

This module provides functionality to parse curriculum structure from the database
and generate specifications for content generation. It serves as the bridge
between the curriculum database and the content generation pipeline.

Key Functions:
- parse_curriculum_from_database() -> List[CurriculumCombination]
- extract_generation_specs() -> List[GenerationSpec]
- get_pending_combinations() -> List[CurriculumCombination]
- update_generation_status() -> bool
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .curriculum_database import (
    CurriculumCombination,
    LanguagePairID,
    CEFRLevelID,
    ContentCategoryID,
    ExerciseTypeID,
    TopicID,
    LANGUAGE_PAIRS,
    CEFR_LEVELS,
    CONTENT_CATEGORIES,
    EXERCISE_TYPES,
    TOPICS
)

logger = logging.getLogger(__name__)

@dataclass
class GenerationSpec:
    """Specification for a single content generation task."""
    id: str
    language_pair: Tuple[str, str]  # (source_lang, target_lang)
    language_pair_name: str  # "Spanish → English"
    level: str  # "B1"
    category: str  # "Vocabulary"
    exercise_type: str  # "Multiple Choice"
    topic: str  # "Daily Life & Routines"
    exercises_target: int
    priority: int
    context_description: str  # Rich context for LLM
    
    # Standardized IDs for schema mapping
    language_pair_id: LanguagePairID
    level_id: CEFRLevelID
    category_id: ContentCategoryID
    exercise_type_id: ExerciseTypeID
    topic_id: TopicID

class CurriculumStructureParser:
    """Parser for curriculum structure and generation specifications."""
    
    def __init__(self, database_url: str = "sqlite:///scripts/curriculum.db"):
        """Initialize the parser with database connection."""
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def parse_curriculum_from_database(self) -> List[CurriculumCombination]:
        """Parse all curriculum combinations from the database.
        
        Returns:
            List of all curriculum combinations in the database.
        """
        session = self.SessionLocal()
        try:
            result = session.execute(text("""
                SELECT id, language_pair_id, level_id, category_id, exercise_type_id, topic_id,
                       generation_status, exercises_generated, exercises_target, last_generated, priority
                FROM curriculum_structure
                ORDER BY priority, id
            """))
            
            combinations = []
            for row in result:
                combination = CurriculumCombination(
                    id=row.id,
                    language_pair_id=LanguagePairID(row.language_pair_id),
                    level_id=CEFRLevelID(row.level_id),
                    category_id=ContentCategoryID(row.category_id),
                    exercise_type_id=ExerciseTypeID(row.exercise_type_id),
                    topic_id=TopicID(row.topic_id),
                    generation_status=row.generation_status,
                    exercises_generated=row.exercises_generated,
                    exercises_target=row.exercises_target,
                    last_generated=row.last_generated.isoformat() if row.last_generated else "",
                    priority=row.priority
                )
                combinations.append(combination)
            
            logger.info(f"Parsed {len(combinations)} curriculum combinations from database")
            return combinations
            
        except Exception as e:
            logger.error(f"Error parsing curriculum from database: {e}")
            raise
        finally:
            session.close()
    
    def extract_generation_specs(self, combinations: Optional[List[CurriculumCombination]] = None) -> List[GenerationSpec]:
        """Extract generation specifications from curriculum combinations.
        
        Args:
            combinations: List of curriculum combinations. If None, will fetch from database.
            
        Returns:
            List of generation specifications ready for content generation.
        """
        if combinations is None:
            combinations = self.parse_curriculum_from_database()
        
        specs = []
        
        for combo in combinations:
            # Get human-readable names and descriptions
            lang_pair = LANGUAGE_PAIRS[combo.language_pair_id]
            level = CEFR_LEVELS[combo.level_id]
            category = CONTENT_CATEGORIES[combo.category_id]
            ex_type = EXERCISE_TYPES[combo.exercise_type_id]
            topic = TOPICS[combo.topic_id]
            
            # Build rich context description for LLM
            context = self._build_context_description(
                lang_pair, level, category, ex_type, topic
            )
            
            spec = GenerationSpec(
                id=combo.id,
                language_pair=(lang_pair.source_lang, lang_pair.target_lang),
                language_pair_name=f"{lang_pair.source_name} → {lang_pair.target_name}",
                level=level.code,
                category=category.name,
                exercise_type=ex_type.name,
                topic=topic.name,
                exercises_target=combo.exercises_target,
                priority=combo.priority,
                context_description=context,
                language_pair_id=combo.language_pair_id,
                level_id=combo.level_id,
                category_id=combo.category_id,
                exercise_type_id=combo.exercise_type_id,
                topic_id=combo.topic_id
            )
            
            specs.append(spec)
        
        logger.info(f"Extracted {len(specs)} generation specifications")
        return specs
    
    def get_pending_combinations(self, limit: Optional[int] = None) -> List[GenerationSpec]:
        """Get pending curriculum combinations for generation.
        
        Args:
            limit: Maximum number of combinations to return. If None, returns all pending.
            
        Returns:
            List of generation specifications with 'pending' status.
        """
        session = self.SessionLocal()
        try:
            limit_clause = f"LIMIT {limit}" if limit else ""
            
            result = session.execute(text(f"""
                SELECT id, language_pair_id, level_id, category_id, exercise_type_id, topic_id,
                       exercises_target, priority
                FROM curriculum_structure
                WHERE generation_status = 'pending'
                ORDER BY priority, id
                {limit_clause}
            """))
            
            pending_combinations = []
            for row in result:
                combo = CurriculumCombination(
                    id=row.id,
                    language_pair_id=LanguagePairID(row.language_pair_id),
                    level_id=CEFRLevelID(row.level_id),
                    category_id=ContentCategoryID(row.category_id),
                    exercise_type_id=ExerciseTypeID(row.exercise_type_id),
                    topic_id=TopicID(row.topic_id),
                    generation_status='pending',
                    exercises_generated=0,
                    exercises_target=row.exercises_target,
                    last_generated="",
                    priority=row.priority
                )
                pending_combinations.append(combo)
            
            # Convert to generation specs
            specs = self.extract_generation_specs(pending_combinations)
            
            logger.info(f"Found {len(specs)} pending combinations for generation")
            return specs
            
        except Exception as e:
            logger.error(f"Error getting pending combinations: {e}")
            raise
        finally:
            session.close()
    
    def update_generation_status(self, combo_id: str, status: str, exercises_generated: int = 0) -> bool:
        """Update the generation status of a curriculum combination.
        
        Args:
            combo_id: The curriculum combination ID (e.g., "COMBO_001")
            status: New status ('pending', 'in_progress', 'completed', 'failed')
            exercises_generated: Number of exercises generated (for completed status)
            
        Returns:
            True if update was successful, False otherwise.
        """
        session = self.SessionLocal()
        try:
            # Validate status
            valid_statuses = ['pending', 'in_progress', 'completed', 'failed']
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
            
            # Update the record
            update_time = datetime.utcnow()
            result = session.execute(text("""
                UPDATE curriculum_structure
                SET generation_status = :status,
                    exercises_generated = :exercises_generated,
                    last_generated = :last_generated,
                    updated_at = :updated_at
                WHERE id = :combo_id
            """), {
                'status': status,
                'exercises_generated': exercises_generated,
                'last_generated': update_time if status == 'completed' else None,
                'updated_at': update_time,
                'combo_id': combo_id
            })
            
            session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Updated {combo_id} status to {status} ({exercises_generated} exercises)")
                return True
            else:
                logger.warning(f"No combination found with ID: {combo_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating generation status: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_combinations_by_filter(self, 
                                 language_pair_id: Optional[LanguagePairID] = None,
                                 level_id: Optional[CEFRLevelID] = None,
                                 category_id: Optional[ContentCategoryID] = None,
                                 exercise_type_id: Optional[ExerciseTypeID] = None,
                                 topic_id: Optional[TopicID] = None) -> List[GenerationSpec]:
        """Get curriculum combinations filtered by specific criteria.
        
        Args:
            language_pair_id: Filter by language pair ID
            level_id: Filter by CEFR level ID
            category_id: Filter by content category ID
            exercise_type_id: Filter by exercise type ID
            topic_id: Filter by topic ID
            
        Returns:
            List of generation specifications matching the filter criteria.
        """
        session = self.SessionLocal()
        try:
            # Build WHERE clause dynamically
            conditions = []
            params = {}
            
            if language_pair_id:
                conditions.append("language_pair_id = :language_pair_id")
                params['language_pair_id'] = language_pair_id.value
            
            if level_id:
                conditions.append("level_id = :level_id")
                params['level_id'] = level_id.value
            
            if category_id:
                conditions.append("category_id = :category_id")
                params['category_id'] = category_id.value
            
            if exercise_type_id:
                conditions.append("exercise_type_id = :exercise_type_id")
                params['exercise_type_id'] = exercise_type_id.value
            
            if topic_id:
                conditions.append("topic_id = :topic_id")
                params['topic_id'] = topic_id.value
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            query = f"""
                SELECT id, language_pair_id, level_id, category_id, exercise_type_id, topic_id,
                       exercises_target, priority
                FROM curriculum_structure
                {where_clause}
                ORDER BY priority, id
            """
            
            result = session.execute(text(query), params)
            
            filtered_combinations = []
            for row in result:
                combo = CurriculumCombination(
                    id=row.id,
                    language_pair_id=LanguagePairID(row.language_pair_id),
                    level_id=CEFRLevelID(row.level_id),
                    category_id=ContentCategoryID(row.category_id),
                    exercise_type_id=ExerciseTypeID(row.exercise_type_id),
                    topic_id=TopicID(row.topic_id),
                    generation_status='pending',
                    exercises_generated=0,
                    exercises_target=row.exercises_target,
                    last_generated="",
                    priority=row.priority
                )
                filtered_combinations.append(combo)
            
            # Convert to generation specs
            specs = self.extract_generation_specs(filtered_combinations)
            
            logger.info(f"Found {len(specs)} combinations matching filter criteria")
            return specs
            
        except Exception as e:
            logger.error(f"Error filtering combinations: {e}")
            raise
        finally:
            session.close()
    
    def _build_context_description(self, lang_pair, level, category, ex_type, topic) -> str:
        """Build rich context description for LLM generation.
        
        Args:
            lang_pair: Language pair object
            level: CEFR level object
            category: Content category object
            ex_type: Exercise type object
            topic: Topic object
            
        Returns:
            Rich context description string.
        """
        context = f"""
Generate {ex_type.name.lower()} exercises for {lang_pair.source_name} speakers learning {lang_pair.target_name}.

**Language Context:**
- Source Language: {lang_pair.source_name} ({lang_pair.source_lang})
- Target Language: {lang_pair.target_name} ({lang_pair.target_lang})

**Proficiency Level:**
- CEFR Level: {level.code} ({level.name})
- Description: {level.description}

**Content Focus:**
- Category: {category.name}
- Description: {category.description}

**Exercise Format:**
- Type: {ex_type.name}
- Description: {ex_type.description}
- WhatsApp Compatible: {ex_type.whatsapp_compatible}

**Topic Context:**
- Topic: {topic.name}
- Description: {topic.description}

**Generation Guidelines:**
- Content should be appropriate for {level.code} level learners
- Exercises must be culturally relevant for {lang_pair.source_name} speakers
- Focus on practical, real-world scenarios related to {topic.name.lower()}
- Ensure exercises are engaging and educational
- Follow standard {ex_type.name.lower()} format with clear instructions
"""
        return context.strip()
    
    def get_generation_statistics(self) -> Dict:
        """Get comprehensive generation statistics.
        
        Returns:
            Dictionary with generation statistics.
        """
        session = self.SessionLocal()
        try:
            result = session.execute(text("""
                SELECT 
                    COUNT(*) as total_combinations,
                    SUM(CASE WHEN generation_status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN generation_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN generation_status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN generation_status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(exercises_target) as total_target_exercises,
                    SUM(exercises_generated) as total_generated_exercises
                FROM curriculum_structure
            """))
            
            stats = result.fetchone()
            
            # Calculate completion rates
            completion_rate = 0.0
            if stats.total_target_exercises > 0:
                completion_rate = (stats.total_generated_exercises / stats.total_target_exercises) * 100
            
            return {
                'total_combinations': stats.total_combinations,
                'completed': stats.completed,
                'pending': stats.pending,
                'in_progress': stats.in_progress,
                'failed': stats.failed,
                'total_target_exercises': stats.total_target_exercises,
                'total_generated_exercises': stats.total_generated_exercises,
                'completion_rate': completion_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting generation statistics: {e}")
            raise
        finally:
            session.close()

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_mvp_generation_specs(database_url: str = "sqlite:///scripts/curriculum.db") -> List[GenerationSpec]:
    """Get MVP generation specifications (all pending combinations).
    
    Args:
        database_url: URL of the curriculum database
        
    Returns:
        List of MVP generation specifications.
    """
    parser = CurriculumStructureParser(database_url)
    return parser.get_pending_combinations()

def get_generation_specs_by_language(source_lang: str, target_lang: str, 
                                   database_url: str = "sqlite:///scripts/curriculum.db") -> List[GenerationSpec]:
    """Get generation specifications for a specific language pair.
    
    Args:
        source_lang: Source language code (e.g., 'es')
        target_lang: Target language code (e.g., 'en')
        database_url: URL of the curriculum database
        
    Returns:
        List of generation specifications for the language pair.
    """
    parser = CurriculumStructureParser(database_url)
    
    # Find the language pair ID
    lang_pair_id = None
    for lp_id, lp in LANGUAGE_PAIRS.items():
        if lp.source_lang == source_lang and lp.target_lang == target_lang:
            lang_pair_id = lp_id
            break
    
    if lang_pair_id is None:
        raise ValueError(f"Language pair {source_lang}→{target_lang} not found")
    
    return parser.get_combinations_by_filter(language_pair_id=lang_pair_id)

if __name__ == "__main__":
    # Demo the parser functionality
    logging.basicConfig(level=logging.INFO)
    
    parser = CurriculumStructureParser()
    
    print("🎓 CURRICULUM STRUCTURE PARSER DEMO")
    print("=" * 60)
    
    # Get all combinations
    all_combinations = parser.parse_curriculum_from_database()
    print(f"📊 Total combinations in database: {len(all_combinations)}")
    
    # Get pending combinations
    pending_specs = parser.get_pending_combinations(limit=5)
    print(f"⏳ Pending combinations (first 5): {len(pending_specs)}")
    
    # Show sample spec
    if pending_specs:
        spec = pending_specs[0]
        print(f"\n🔍 Sample Generation Spec:")
        print(f"   ID: {spec.id}")
        print(f"   Language: {spec.language_pair_name}")
        print(f"   Level: {spec.level}")
        print(f"   Category: {spec.category}")
        print(f"   Exercise: {spec.exercise_type}")
        print(f"   Topic: {spec.topic}")
        print(f"   Target: {spec.exercises_target} exercises")
    
    # Get statistics
    stats = parser.get_generation_statistics()
    print(f"\n📈 Generation Statistics:")
    print(f"   Total: {stats['total_combinations']}")
    print(f"   Pending: {stats['pending']}")
    print(f"   Completed: {stats['completed']}")
    print(f"   Completion Rate: {stats['completion_rate']:.1f}%")
    
    print("\n✅ Parser demo completed!")
