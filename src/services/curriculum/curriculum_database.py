"""Curriculum Database - Parsed curriculum structure with standardized IDs.

This file contains the parsed curriculum structure as a database with standardized IDs
for exercise types, content categories, and topics. This serves as the source of truth
for content generation.

Database Structure:
- Language Pairs: LANG_001, LANG_002, etc.
- CEFR Levels: LEVEL_A1, LEVEL_A2, LEVEL_B1, LEVEL_B2, LEVEL_C1, LEVEL_C2
- Content Categories: CAT_VOCAB, CAT_GRAMMAR, CAT_FUNCTIONAL, CAT_CONVERSATION, CAT_CULTURAL
- Exercise Types: EX_MCQ, EX_FILL, EX_ROLEPLAY, EX_OPEN, EX_TRANS, EX_ERROR, etc.
- Topics: TOPIC_DAILY, TOPIC_FOOD, TOPIC_WORK, etc.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# STANDARDIZED ID SYSTEM
# ============================================================================

class LanguagePairID(Enum):
    """Standardized language pair identifiers."""
    SPANISH_TO_ENGLISH = "LANG_001"
    PORTUGUESE_TO_ENGLISH = "LANG_002"
    ENGLISH_TO_SPANISH = "LANG_003"
    ENGLISH_TO_PORTUGUESE = "LANG_004"
    FRENCH_TO_ENGLISH = "LANG_005"  # Future
    ENGLISH_TO_FRENCH = "LANG_006"  # Future
    GERMAN_TO_ENGLISH = "LANG_007"   # Future
    ENGLISH_TO_GERMAN = "LANG_008"   # Future
    ITALIAN_TO_ENGLISH = "LANG_009"   # Future
    ENGLISH_TO_ITALIAN = "LANG_010"   # Future

class CEFRLevelID(Enum):
    """Standardized CEFR level identifiers."""
    A1 = "LEVEL_A1"
    A2 = "LEVEL_A2"
    B1 = "LEVEL_B1"
    B2 = "LEVEL_B2"
    C1 = "LEVEL_C1"
    C2 = "LEVEL_C2"

class ContentCategoryID(Enum):
    """Standardized content category identifiers."""
    VOCABULARY = "CAT_VOCAB"
    GRAMMAR = "CAT_GRAMMAR"
    FUNCTIONAL_LANGUAGE = "CAT_FUNCTIONAL"
    CONVERSATION_SKILLS = "CAT_CONVERSATION"
    CULTURAL_COMPETENCE = "CAT_CULTURAL"

class ExerciseTypeID(Enum):
    """Standardized exercise type identifiers."""
    MULTIPLE_CHOICE = "EX_MCQ"
    FILL_IN_BLANK = "EX_FILL"
    ROLEPLAY = "EX_ROLEPLAY"
    OPEN_RESPONSE = "EX_OPEN"
    TRANSLATION = "EX_TRANS"
    ERROR_IDENTIFICATION = "EX_ERROR"
    VOICE_MULTIPLE_CHOICE = "EX_VOICE_MCQ"
    VOICE_INPUT = "EX_VOICE_INPUT"
    CONVERSATION_ROLES = "EX_CONVERSATION"
    MATCHING = "EX_MATCHING"
    SORTING = "EX_SORTING"

class TopicID(Enum):
    """Standardized topic identifiers."""
    DAILY_LIFE_ROUTINES = "TOPIC_DAILY"
    FOOD_DINING = "TOPIC_FOOD"
    WORK_PROFESSIONAL = "TOPIC_WORK"
    TRAVEL_GEOGRAPHY = "TOPIC_TRAVEL"
    SOCIAL_RELATIONSHIPS = "TOPIC_SOCIAL"
    SHOPPING_ERRANDS = "TOPIC_SHOPPING"
    HEALTH_WELLNESS = "TOPIC_HEALTH"
    CULTURE_ENTERTAINMENT = "TOPIC_CULTURE"
    EDUCATION_LEARNING = "TOPIC_EDUCATION"

# ============================================================================
# CURRICULUM DATABASE STRUCTURE
# ============================================================================

@dataclass
class LanguagePair:
    """Language pair definition."""
    id: LanguagePairID
    source_lang: str
    target_lang: str
    source_name: str
    target_name: str
    is_active: bool
    priority: int  # 1= highest priority

@dataclass
class CEFRLevel:
    """CEFR level definition."""
    id: CEFRLevelID
    code: str
    name: str
    description: str
    is_active: bool

@dataclass
class ContentCategory:
    """Content category definition."""
    id: ContentCategoryID
    name: str
    description: str
    is_active: bool

@dataclass
class ExerciseType:
    """Exercise type definition."""
    id: ExerciseTypeID
    name: str
    description: str
    is_active: bool
    requires_audio: bool
    whatsapp_compatible: bool

@dataclass
class Topic:
    """Topic definition."""
    id: TopicID
    name: str
    description: str
    is_active: bool
    priority: int  # 1= highest priority

@dataclass
class CurriculumCombination:
    """Single curriculum combination (one row in the generation database)."""
    id: str  # Generated unique ID
    language_pair_id: LanguagePairID
    level_id: CEFRLevelID
    category_id: ContentCategoryID
    exercise_type_id: ExerciseTypeID
    topic_id: TopicID
    generation_status: str  # "pending", "in_progress", "completed", "failed"
    exercises_generated: int
    exercises_target: int
    last_generated: str  # ISO timestamp
    priority: int  # Generation priority

# ============================================================================
# MASTER DATABASE RECORDS
# ============================================================================

LANGUAGE_PAIRS = {
    LanguagePairID.SPANISH_TO_ENGLISH: LanguagePair(
        id=LanguagePairID.SPANISH_TO_ENGLISH,
        source_lang="es",
        target_lang="en", 
        source_name="Spanish",
        target_name="English",
        is_active=True,
        priority=1
    ),
    LanguagePairID.PORTUGUESE_TO_ENGLISH: LanguagePair(
        id=LanguagePairID.PORTUGUESE_TO_ENGLISH,
        source_lang="pt",
        target_lang="en",
        source_name="Portuguese", 
        target_name="English",
        is_active=True,
        priority=2
    ),
    LanguagePairID.ENGLISH_TO_SPANISH: LanguagePair(
        id=LanguagePairID.ENGLISH_TO_SPANISH,
        source_lang="en",
        target_lang="es",
        source_name="English",
        target_name="Spanish",
        is_active=False,  # Future
        priority=3
    ),
    LanguagePairID.ENGLISH_TO_PORTUGUESE: LanguagePair(
        id=LanguagePairID.ENGLISH_TO_PORTUGUESE,
        source_lang="en", 
        target_lang="pt",
        source_name="English",
        target_name="Portuguese",
        is_active=False,  # Future
        priority=4
    ),
}

CEFR_LEVELS = {
    CEFRLevelID.A1: CEFRLevel(
        id=CEFRLevelID.A1,
        code="A1",
        name="Beginner",
        description="Basic phrases, survival communication",
        is_active=False  # Future
    ),
    CEFRLevelID.A2: CEFRLevel(
        id=CEFRLevelID.A2,
        code="A2", 
        name="Elementary",
        description="Simple conversations, routine tasks",
        is_active=False  # Future
    ),
    CEFRLevelID.B1: CEFRLevel(
        id=CEFRLevelID.B1,
        code="B1",
        name="Intermediate", 
        description="Independent communication, opinions",
        is_active=True  # Current focus
    ),
    CEFRLevelID.B2: CEFRLevel(
        id=CEFRLevelID.B2,
        code="B2",
        name="Upper-Intermediate",
        description="Complex ideas, nuanced expression",
        is_active=False  # Future
    ),
    CEFRLevelID.C1: CEFRLevel(
        id=CEFRLevelID.C1,
        code="C1",
        name="Advanced",
        description="Professional/academic contexts",
        is_active=False  # Future
    ),
    CEFRLevelID.C2: CEFRLevel(
        id=CEFRLevelID.C2,
        code="C2",
        name="Proficient",
        description="Near-native fluency",
        is_active=False  # Future
    ),
}

CONTENT_CATEGORIES = {
    ContentCategoryID.VOCABULARY: ContentCategory(
        id=ContentCategoryID.VOCABULARY,
        name="Vocabulary",
        description="Words, phrases, expressions, terminology",
        is_active=True  # Current focus
    ),
    ContentCategoryID.GRAMMAR: ContentCategory(
        id=ContentCategoryID.GRAMMAR,
        name="Grammar",
        description="Structure, rules, patterns, syntax",
        is_active=True  # Current focus
    ),
    ContentCategoryID.FUNCTIONAL_LANGUAGE: ContentCategory(
        id=ContentCategoryID.FUNCTIONAL_LANGUAGE,
        name="Functional Language",
        description="Practical expressions for real situations",
        is_active=True  # Current focus
    ),
    ContentCategoryID.CONVERSATION_SKILLS: ContentCategory(
        id=ContentCategoryID.CONVERSATION_SKILLS,
        name="Conversation Skills",
        description="Dialogue practice, communication strategies",
        is_active=False  # Future
    ),
    ContentCategoryID.CULTURAL_COMPETENCE: ContentCategory(
        id=ContentCategoryID.CULTURAL_COMPETENCE,
        name="Cultural Competence",
        description="Social norms, cultural context, pragmatics",
        is_active=False  # Future
    ),
}

EXERCISE_TYPES = {
    ExerciseTypeID.MULTIPLE_CHOICE: ExerciseType(
        id=ExerciseTypeID.MULTIPLE_CHOICE,
        name="Multiple Choice",
        description="Text-based - Select correct answer from options",
        is_active=True,  # Current focus
        requires_audio=False,
        whatsapp_compatible=True
    ),
    ExerciseTypeID.FILL_IN_BLANK: ExerciseType(
        id=ExerciseTypeID.FILL_IN_BLANK,
        name="Fill in the Blank",
        description="Text-based - Complete missing parts in sentences",
        is_active=True,  # Current focus
        requires_audio=False,
        whatsapp_compatible=True
    ),
    ExerciseTypeID.ROLEPLAY: ExerciseType(
        id=ExerciseTypeID.ROLEPLAY,
        name="Roleplay",
        description="Text-based - Simulated conversations/scenarios",
        is_active=True,  # Current focus
        requires_audio=False,
        whatsapp_compatible=True
    ),
    ExerciseTypeID.OPEN_RESPONSE: ExerciseType(
        id=ExerciseTypeID.OPEN_RESPONSE,
        name="Open Response",
        description="Text-based - Free-form answers",
        is_active=False,  # Future
        requires_audio=False,
        whatsapp_compatible=True
    ),
    ExerciseTypeID.TRANSLATION: ExerciseType(
        id=ExerciseTypeID.TRANSLATION,
        name="Translation",
        description="Text-to-text - Convert between languages",
        is_active=False,  # Future
        requires_audio=False,
        whatsapp_compatible=True
    ),
    ExerciseTypeID.ERROR_IDENTIFICATION: ExerciseType(
        id=ExerciseTypeID.ERROR_IDENTIFICATION,
        name="Error Identification",
        description="Text-based - Find and correct mistakes",
        is_active=False,  # Future
        requires_audio=False,
        whatsapp_compatible=True
    ),
    ExerciseTypeID.VOICE_MULTIPLE_CHOICE: ExerciseType(
        id=ExerciseTypeID.VOICE_MULTIPLE_CHOICE,
        name="Voice Multiple Choice",
        description="Speech-to-text - Select correct audio option as text",
        is_active=False,  # Future
        requires_audio=True,
        whatsapp_compatible=False
    ),
    ExerciseTypeID.VOICE_INPUT: ExerciseType(
        id=ExerciseTypeID.VOICE_INPUT,
        name="Voice Input",
        description="Speech-to-text - Speak answers given as text, pronunciation practice",
        is_active=False,  # Future
        requires_audio=True,
        whatsapp_compatible=False
    ),
}

TOPICS = {
    TopicID.DAILY_LIFE_ROUTINES: Topic(
        id=TopicID.DAILY_LIFE_ROUTINES,
        name="Daily Life & Routines",
        description="Personal care, home activities, time management, sleep, organization",
        is_active=True,
        priority=1
    ),
    TopicID.FOOD_DINING: Topic(
        id=TopicID.FOOD_DINING,
        name="Food & Dining",
        description="Basic foods, meals, cooking, restaurants, dietary preferences, beverages",
        is_active=True,
        priority=2
    ),
    TopicID.WORK_PROFESSIONAL: Topic(
        id=TopicID.WORK_PROFESSIONAL,
        name="Work & Professional",
        description="Office environment, job roles, business communication, workplace interactions, career development",
        is_active=True,
        priority=3
    ),
    TopicID.TRAVEL_GEOGRAPHY: Topic(
        id=TopicID.TRAVEL_GEOGRAPHY,
        name="Travel & Geography",
        description="Transportation, directions, accommodations, destinations, travel preparation, geography",
        is_active=True,
        priority=4
    ),
    TopicID.SOCIAL_RELATIONSHIPS: Topic(
        id=TopicID.SOCIAL_RELATIONSHIPS,
        name="Social & Relationships",
        description="Family members, friends, romantic relationships, social events, communication, emotions",
        is_active=False,  # Lower priority for MVP
        priority=5
    ),
    TopicID.SHOPPING_ERRANDS: Topic(
        id=TopicID.SHOPPING_ERRANDS,
        name="Shopping & Errands",
        description="Clothing, colors, stores, money, services, consumer goods",
        is_active=False,  # Lower priority for MVP
        priority=6
    ),
    TopicID.HEALTH_WELLNESS: Topic(
        id=TopicID.HEALTH_WELLNESS,
        name="Health & Wellness",
        description="Body parts, illnesses, medical care, fitness, mental health, nutrition",
        is_active=False,  # Lower priority for MVP
        priority=7
    ),
    TopicID.CULTURE_ENTERTAINMENT: Topic(
        id=TopicID.CULTURE_ENTERTAINMENT,
        name="Culture & Entertainment",
        description="Animals, media, hobbies, arts, celebrations, technology",
        is_active=False,  # Lower priority for MVP
        priority=8
    ),
    TopicID.EDUCATION_LEARNING: Topic(
        id=TopicID.EDUCATION_LEARNING,
        name="Education & Learning",
        description="Institutions, classroom objects, subjects, assessments, student life, learning activities",
        is_active=False,  # Lower priority for MVP
        priority=9
    ),
}

# ============================================================================
# MVP CURRICULUM COMBINATIONS
# ============================================================================

def generate_mvp_combinations() -> List[CurriculumCombination]:
    """Generate MVP curriculum combinations for current focus.
    
    Current Focus:
    - Language Pairs: Spanish→English, Portuguese→English
    - CEFR Level: B1
    - Content Categories: Vocabulary, Grammar, Functional Language
    - Exercise Types: Multiple Choice, Fill in Blank, Roleplay
    - Topics: Daily Life, Food & Dining, Work & Professional (top 3 priority topics)
    
    Returns: 2 × 1 × 3 × 3 × 3 = 54 combinations
    """
    combinations = []
    
    # MVP parameters
    active_language_pairs = [
        LanguagePairID.SPANISH_TO_ENGLISH,
        LanguagePairID.PORTUGUESE_TO_ENGLISH
    ]
    active_level = CEFRLevelID.B1
    active_categories = [
        ContentCategoryID.VOCABULARY,
        ContentCategoryID.GRAMMAR,
        ContentCategoryID.FUNCTIONAL_LANGUAGE
    ]
    active_exercise_types = [
        ExerciseTypeID.MULTIPLE_CHOICE,
        ExerciseTypeID.FILL_IN_BLANK,
        ExerciseTypeID.ROLEPLAY
    ]
    active_topics = [
        TopicID.DAILY_LIFE_ROUTINES,
        TopicID.FOOD_DINING,
        TopicID.WORK_PROFESSIONAL
    ]
    
    combination_id = 1
    
    for lang_pair in active_language_pairs:
        for category in active_categories:
            for exercise_type in active_exercise_types:
                for topic in active_topics:
                    # Generate unique ID
                    combo_id = f"COMBO_{combination_id:03d}"
                    
                    # Calculate priority based on component priorities
                    lang_priority = LANGUAGE_PAIRS[lang_pair].priority
                    topic_priority = TOPICS[topic].priority
                    # Higher priority = lower number (1 is highest)
                    overall_priority = (lang_priority * 100) + topic_priority
                    
                    combination = CurriculumCombination(
                        id=combo_id,
                        language_pair_id=lang_pair,
                        level_id=active_level,
                        category_id=category,
                        exercise_type_id=exercise_type,
                        topic_id=topic,
                        generation_status="pending",
                        exercises_generated=0,
                        exercises_target=20,  # Target 20 exercises per combination
                        last_generated="",
                        priority=overall_priority
                    )
                    
                    combinations.append(combination)
                    combination_id += 1
    
    return combinations

# ============================================================================
# DATABASE ACCESS FUNCTIONS
# ============================================================================

def get_active_language_pairs() -> List[LanguagePair]:
    """Get all active language pairs."""
    return [pair for pair in LANGUAGE_PAIRS.values() if pair.is_active]

def get_active_cefr_levels() -> List[CEFRLevel]:
    """Get all active CEFR levels."""
    return [level for level in CEFR_LEVELS.values() if level.is_active]

def get_active_content_categories() -> List[ContentCategory]:
    """Get all active content categories."""
    return [category for category in CONTENT_CATEGORIES.values() if category.is_active]

def get_active_exercise_types() -> List[ExerciseType]:
    """Get all active exercise types."""
    return [ex_type for ex_type in EXERCISE_TYPES.values() if ex_type.is_active]

def get_active_topics() -> List[Topic]:
    """Get all active topics, sorted by priority."""
    active_topics = [topic for topic in TOPICS.values() if topic.is_active]
    return sorted(active_topics, key=lambda t: t.priority)

def get_mvp_curriculum_matrix() -> List[CurriculumCombination]:
    """Get the MVP curriculum matrix for content generation."""
    return generate_mvp_combinations()

def get_combination_by_id(combo_id: str) -> CurriculumCombination:
    """Get a specific curriculum combination by ID."""
    all_combinations = generate_mvp_combinations()
    for combo in all_combinations:
        if combo.id == combo_id:
            return combo
    raise ValueError(f"Curriculum combination {combo_id} not found")

# ============================================================================
# EXAMPLE USAGE AND SAMPLE DATA
# ============================================================================

def print_mvp_summary():
    """Print a summary of the MVP curriculum matrix."""
    combinations = get_mvp_curriculum_matrix()
    
    print("📚 MVP CURRICULUM MATRIX SUMMARY")
    print("=" * 50)
    print(f"Total Combinations: {len(combinations)}")
    print()
    
    # Group by language pair
    by_language = {}
    for combo in combinations:
        lang_pair = LANGUAGE_PAIRS[combo.language_pair_id]
        lang_name = f"{lang_pair.source_name} → {lang_pair.target_name}"
        if lang_name not in by_language:
            by_language[lang_name] = []
        by_language[lang_name].append(combo)
    
    for lang_name, lang_combos in by_language.items():
        print(f"🌍 {lang_name}")
        print(f"   Combinations: {len(lang_combos)}")
        
        # Group by category
        by_category = {}
        for combo in lang_combos:
            category = CONTENT_CATEGORIES[combo.category_id].name
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(combo)
        
        for category, cat_combos in by_category.items():
            print(f"     📖 {category}: {len(cat_combos)} combinations")
            
            # Show exercise types and topics
            exercise_types = set()
            topics = set()
            for combo in cat_combos:
                exercise_types.add(EXERCISE_TYPES[combo.exercise_type_id].name)
                topics.add(TOPICS[combo.topic_id].name)
            
            print(f"        Types: {', '.join(exercise_types)}")
            print(f"        Topics: {', '.join(topics)}")
        print()

if __name__ == "__main__":
    print_mvp_summary()
