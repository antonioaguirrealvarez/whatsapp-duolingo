"""Multi-language curriculum seed generator."""

import asyncio
import logging
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.data.models import LanguageLevel, ExerciseType, Topic
from src.data.repositories.exercise import ExerciseRepository
from src.data.repositories.user import UserRepository
from src.services.llm.content_generation import ContentGenerationAgent
from src.data import get_db_session

logger = logging.getLogger(__name__)


class CurriculumSeedGenerator:
    """Generator for multi-language curriculum seed data."""
    
    def __init__(self, db_session: Session):
        """
        Initialize the curriculum seed generator.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self.exercise_repo = ExerciseRepository(db_session)
        self.user_repo = UserRepository(db_session)
        self.content_agent = ContentGenerationAgent(db_session)
        
        # Define language pairs to generate content for
        self.language_pairs = [
            ("es", "en"),  # Spanish to English
            ("en", "es"),  # English to Spanish
            ("fr", "en"),  # French to English
            ("en", "fr"),  # English to French
            ("de", "en"),  # German to English
            ("en", "de"),  # English to German
            ("pt", "en"),  # Portuguese to English
            ("en", "pt"),  # English to Portuguese
            ("it", "en"),  # Italian to English
            ("en", "it"),  # English to Italian
        ]
        
        # Define topics for each level
        self.topics_by_level = {
            LanguageLevel.A1: [
                "Greetings and Introductions",
                "Basic Numbers and Time",
                "Family and Friends",
                "Food and Drinks",
                "Daily Activities",
                "Colors and Shapes",
                "Animals and Nature",
                "Basic Questions",
                "Weather and Seasons",
                "Transportation"
            ],
            LanguageLevel.A2: [
                "Shopping and Commerce",
                "Travel and Directions",
                "Hobbies and Interests",
                "Work and Professions",
                "Health and Body",
                "Clothing and Appearance",
                "Home and Furniture",
                "Emotions and Feelings",
                "Technology and Internet",
                "Sports and Exercise"
            ],
            LanguageLevel.B1: [
                "Current Events and News",
                "Culture and Traditions",
                "Education and Learning",
                "Environment and Conservation",
                "Movies and Entertainment",
                "Science and Technology",
                "Business and Economy",
                "History and Geography",
                "Literature and Arts",
                "Social Issues"
            ],
            LanguageLevel.B2: [
                "Politics and Government",
                "Philosophy and Ethics",
                "Advanced Science Topics",
                "Economic Concepts",
                "Legal Systems",
                "Academic Subjects",
                "Professional Communication",
                "Cultural Analysis",
                "Global Issues",
                "Specialized Fields"
            ]
        }
    
    async def generate_full_curriculum(
        self,
        exercises_per_topic: int = 20,
        max_concurrent_generations: int = 3
    ) -> Dict[str, any]:
        """
        Generate full curriculum for all language pairs and levels.
        
        Args:
            exercises_per_topic: Number of exercises to generate per topic
            max_concurrent_generations: Maximum concurrent generation tasks
            
        Returns:
            Dictionary with generation results
        """
        logger.info("Starting full curriculum generation...")
        
        results = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_exercises_generated": 0,
            "language_pairs": {},
            "errors": []
        }
        
        # Create semaphore to limit concurrent generations
        semaphore = asyncio.Semaphore(max_concurrent_generations)
        
        # Generate tasks for all language pairs and levels
        tasks = []
        for source_lang, target_lang in self.language_pairs:
            for level in LanguageLevel:
                if level in self.topics_by_level:
                    for topic in self.topics_by_level[level]:
                        for exercise_type in ExerciseType:
                            task = self._generate_topic_exercises(
                                semaphore, source_lang, target_lang, 
                                level, topic, exercise_type, exercises_per_topic
                            )
                            tasks.append(task)
        
        # Execute all tasks
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in task_results:
            if isinstance(result, Exception):
                results["failed_generations"] += 1
                results["errors"].append(str(result))
            else:
                results["total_generations"] += 1
                if result["success"]:
                    results["successful_generations"] += 1
                    results["total_exercises_generated"] += result["generated_count"]
                    
                    # Track by language pair
                    pair_key = f"{result['source_lang']}->{result['target_lang']}"
                    if pair_key not in results["language_pairs"]:
                        results["language_pairs"][pair_key] = {
                            "successful": 0,
                            "exercises": 0
                        }
                    results["language_pairs"][pair_key]["successful"] += 1
                    results["language_pairs"][pair_key]["exercises"] += result["generated_count"]
                else:
                    results["failed_generations"] += 1
                    results["errors"].append(result.get("error", "Unknown error"))
        
        logger.info(f"Curriculum generation completed: {results}")
        return results
    
    async def _generate_topic_exercises(
        self,
        semaphore: asyncio.Semaphore,
        source_lang: str,
        target_lang: str,
        level: LanguageLevel,
        topic: str,
        exercise_type: ExerciseType,
        count: int
    ) -> Dict[str, any]:
        """
        Generate exercises for a specific topic with concurrency control.
        
        Args:
            semaphore: Semaphore for concurrency control
            source_lang: Source language code
            target_lang: Target language code
            level: Language level
            topic: Topic name
            exercise_type: Exercise type
            count: Number of exercises to generate
            
        Returns:
            Generation result dictionary
        """
        async with semaphore:
            try:
                # Check if exercises already exist for this combination
                existing_count = self.exercise_repo.count_by_language_pair(source_lang, target_lang)
                if existing_count > 1000:  # Skip if we already have enough content
                    logger.info(f"Skipping {source_lang}->{target_lang} {level} {topic} - already have {existing_count} exercises")
                    return {
                        "success": True,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "level": level.value,
                        "topic": topic,
                        "exercise_type": exercise_type.value,
                        "generated_count": 0,
                        "saved_count": 0,
                        "skipped": True
                    }
                
                logger.info(f"Generating {count} {exercise_type.value} exercises for {source_lang}->{target_lang} {level} {topic}")
                
                result = await self.content_agent.generate_exercises(
                    source_lang=source_lang,
                    target_lang=target_lang,
                    difficulty=level,
                    exercise_type=exercise_type,
                    topic=topic,
                    count=count,
                    save_to_db=True
                )
                
                # Add metadata to result
                result.update({
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "level": level.value,
                    "topic": topic,
                    "exercise_type": exercise_type.value
                })
                
                if result["success"]:
                    logger.info(f"Successfully generated {result['generated_count']} exercises for {topic}")
                else:
                    logger.error(f"Failed to generate exercises for {topic}: {result.get('error')}")
                
                return result
                
            except Exception as e:
                logger.error(f"Error generating exercises for {topic}: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "level": level.value,
                    "topic": topic,
                    "exercise_type": exercise_type.value,
                    "generated_count": 0,
                    "saved_count": 0
                }
    
    def create_seed_topics(self) -> List[Topic]:
        """
        Create seed topics in the database.
        
        Returns:
            List of created topics
        """
        topics = []
        
        # Collect all unique topics
        all_topics = set()
        for level_topics in self.topics_by_level.values():
            all_topics.update(level_topics)
        
        # Create topics if they don't exist
        for topic_name in all_topics:
            existing_topic = self.exercise_repo.get_by_field("name", topic_name)
            if not existing_topic:
                topic = Topic(
                    name=topic_name,
                    description=f"Learning exercises for {topic_name}"
                )
                self.db_session.add(topic)
                topics.append(topic)
        
        self.db_session.commit()
        logger.info(f"Created {len(topics)} seed topics")
        
        return topics
    
    def generate_sample_users(self, count: int = 100) -> List[Dict]:
        """
        Generate sample users for testing.
        
        Args:
            count: Number of users to generate
            
        Returns:
            List of generated user data
        """
        users = []
        
        # Sample names and phone numbers
        sample_names = [
            "Maria Garcia", "John Smith", "Li Wei", "Ahmed Hassan",
            "Sophie Martin", "Carlos Rodriguez", "Emma Wilson", "Yuki Tanaka",
            "Giuseppe Rossi", "Ana Silva", "Hans Mueller", "Elena Petrova"
        ]
        
        for i in range(count):
            # Randomly select language pair
            source_lang, target_lang = self.language_pairs[i % len(self.language_pairs)]
            
            # Randomly select level
            level = list(LanguageLevel)[i % len(LanguageLevel)]
            
            # Create user
            user_data = {
                "wa_id": f"sample_user_{i+1}",
                "name": sample_names[i % len(sample_names)],
                "phone": f"+123456789{i:03d}",
                "native_lang": source_lang,
                "target_lang": target_lang,
                "level": level,
                "is_premium": i % 10 == 0,  # 10% premium users
                "daily_lessons_count": 0,
                "streak_days": 0
            }
            
            user, created = self.user_repo.get_or_create_user(**user_data)
            if created:
                users.append(user_data)
        
        logger.info(f"Created {len(users)} sample users")
        return users
    
    async def generate_quick_seed(
        self,
        exercises_per_language_pair: int = 100
    ) -> Dict[str, any]:
        """
        Generate a quick seed with basic exercises for all language pairs.
        
        Args:
            exercises_per_language_pair: Number of exercises per language pair
            
        Returns:
            Generation results
        """
        logger.info("Starting quick curriculum seed generation...")
        
        results = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_exercises_generated": 0,
            "language_pairs": {}
        }
        
        # Generate basic exercises for each language pair
        for source_lang, target_lang in self.language_pairs:
            try:
                # Generate mixed exercise types for A1 level
                result = await self.content_agent.generate_exercises(
                    source_lang=source_lang,
                    target_lang=target_lang,
                    difficulty=LanguageLevel.A1,
                    exercise_type=ExerciseType.TRANSLATION,
                    topic="Basic Phrases",
                    count=exercises_per_language_pair // 4,
                    save_to_db=True
                )
                
                results["total_generations"] += 1
                if result["success"]:
                    results["successful_generations"] += 1
                    results["total_exercises_generated"] += result["generated_count"]
                    
                    pair_key = f"{source_lang}->{target_lang}"
                    results["language_pairs"][pair_key] = {
                        "exercises": result["generated_count"]
                    }
                else:
                    results["failed_generations"] += 1
                    
            except Exception as e:
                logger.error(f"Error generating quick seed for {source_lang}->{target_lang}: {str(e)}")
                results["failed_generations"] += 1
        
        logger.info(f"Quick seed generation completed: {results}")
        return results


async def main():
    """Main function to run curriculum seeding."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Get database session
    db_session = next(get_db_session())
    
    try:
        # Create seed generator
        generator = CurriculumSeedGenerator(db_session)
        
        # Create seed topics
        generator.create_seed_topics()
        
        # Generate sample users
        generator.generate_sample_users(50)
        
        # Generate quick seed (commented out to avoid API costs)
        # Uncomment to run actual generation:
        # await generator.generate_quick_seed(exercises_per_language_pair=50)
        
        print("Curriculum seed setup completed successfully!")
        print("To generate actual exercises, uncomment the quick seed generation line.")
        
    except Exception as e:
        logger.error(f"Error in curriculum seeding: {str(e)}")
        raise
    finally:
        db_session.close()


if __name__ == "__main__":
    asyncio.run(main())
