#!/usr/bin/env python3
"""Initialize Curriculum Database

This script creates the curriculum database tables and populates them with
the structured curriculum data. This creates the foundation for the
content generation pipeline.

Usage:
    python scripts/init_curriculum_database.py [--force]
"""

import sys
import os
import argparse
from typing import List
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base

from services.curriculum.curriculum_database import (
    get_mvp_curriculum_matrix,
    get_active_language_pairs,
    get_active_cefr_levels,
    get_active_content_categories,
    get_active_exercise_types,
    get_active_topics,
    LANGUAGE_PAIRS,
    CEFR_LEVELS,
    CONTENT_CATEGORIES,
    EXERCISE_TYPES,
    TOPICS
)

Base = declarative_base()

# ============================================================================
# DATABASE MODELS
# ============================================================================

class LanguagePairDB(Base):
    """Database model for language pairs."""
    __tablename__ = 'language_pairs'
    
    id = Column(String(20), primary_key=True)  # LANG_001, etc.
    source_lang = Column(String(5), nullable=False)
    target_lang = Column(String(5), nullable=False)
    source_name = Column(String(50), nullable=False)
    target_name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CEFRLevelDB(Base):
    """Database model for CEFR levels."""
    __tablename__ = 'cefr_levels'
    
    id = Column(String(20), primary_key=True)  # LEVEL_A1, etc.
    code = Column(String(5), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContentCategoryDB(Base):
    """Database model for content categories."""
    __tablename__ = 'content_categories'
    
    id = Column(String(20), primary_key=True)  # CAT_VOCAB, etc.
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExerciseTypeDB(Base):
    """Database model for exercise types."""
    __tablename__ = 'exercise_types'
    
    id = Column(String(20), primary_key=True)  # EX_MCQ, etc.
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    requires_audio = Column(Boolean, default=False)
    whatsapp_compatible = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TopicDB(Base):
    """Database model for topics."""
    __tablename__ = 'topics'
    
    id = Column(String(20), primary_key=True)  # TOPIC_DAILY, etc.
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CurriculumStructureDB(Base):
    """Database model for curriculum structure (the combinations to generate)."""
    __tablename__ = 'curriculum_structure'
    
    id = Column(String(20), primary_key=True)  # COMBO_001, etc.
    language_pair_id = Column(String(20), nullable=False)
    level_id = Column(String(20), nullable=False)
    category_id = Column(String(20), nullable=False)
    exercise_type_id = Column(String(20), nullable=False)
    topic_id = Column(String(20), nullable=False)
    
    generation_status = Column(String(20), default='pending')  # pending, in_progress, completed, failed
    exercises_generated = Column(Integer, default=0)
    exercises_target = Column(Integer, nullable=False)
    last_generated = Column(DateTime)
    priority = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def create_database_schema(engine):
    """Create all database tables."""
    print("🏗️  Creating database schema...")
    Base.metadata.create_all(engine)
    print("✅ Database schema created successfully!")

def populate_language_pairs(session: Session):
    """Populate language pairs table."""
    print("🌍 Populating language pairs...")
    
    for lang_pair in LANGUAGE_PAIRS.values():
        # Check if already exists
        existing = session.query(LanguagePairDB).filter_by(id=lang_pair.id.value).first()
        if existing:
            print(f"   ⏭️  Skipping {lang_pair.id.value} (already exists)")
            continue
        
        db_pair = LanguagePairDB(
            id=lang_pair.id.value,
            source_lang=lang_pair.source_lang,
            target_lang=lang_pair.target_lang,
            source_name=lang_pair.source_name,
            target_name=lang_pair.target_name,
            is_active=lang_pair.is_active,
            priority=lang_pair.priority
        )
        session.add(db_pair)
        print(f"   ✅ Added {lang_pair.id.value}: {lang_pair.source_name} → {lang_pair.target_name}")
    
    session.commit()
    print("✅ Language pairs populated successfully!")

def populate_cefr_levels(session: Session):
    """Populate CEFR levels table."""
    print("📚 Populating CEFR levels...")
    
    for level in CEFR_LEVELS.values():
        # Check if already exists
        existing = session.query(CEFRLevelDB).filter_by(id=level.id.value).first()
        if existing:
            print(f"   ⏭️  Skipping {level.id.value} (already exists)")
            continue
        
        db_level = CEFRLevelDB(
            id=level.id.value,
            code=level.code,
            name=level.name,
            description=level.description,
            is_active=level.is_active
        )
        session.add(db_level)
        print(f"   ✅ Added {level.id.value}: {level.name} ({level.code})")
    
    session.commit()
    print("✅ CEFR levels populated successfully!")

def populate_content_categories(session: Session):
    """Populate content categories table."""
    print("📖 Populating content categories...")
    
    for category in CONTENT_CATEGORIES.values():
        # Check if already exists
        existing = session.query(ContentCategoryDB).filter_by(id=category.id.value).first()
        if existing:
            print(f"   ⏭️  Skipping {category.id.value} (already exists)")
            continue
        
        db_category = ContentCategoryDB(
            id=category.id.value,
            name=category.name,
            description=category.description,
            is_active=category.is_active
        )
        session.add(db_category)
        print(f"   ✅ Added {category.id.value}: {category.name}")
    
    session.commit()
    print("✅ Content categories populated successfully!")

def populate_exercise_types(session: Session):
    """Populate exercise types table."""
    print("✏️  Populating exercise types...")
    
    for ex_type in EXERCISE_TYPES.values():
        # Check if already exists
        existing = session.query(ExerciseTypeDB).filter_by(id=ex_type.id.value).first()
        if existing:
            print(f"   ⏭️  Skipping {ex_type.id.value} (already exists)")
            continue
        
        db_ex_type = ExerciseTypeDB(
            id=ex_type.id.value,
            name=ex_type.name,
            description=ex_type.description,
            is_active=ex_type.is_active,
            requires_audio=ex_type.requires_audio,
            whatsapp_compatible=ex_type.whatsapp_compatible
        )
        session.add(db_ex_type)
        compatible = "✅" if ex_type.whatsapp_compatible else "❌"
        print(f"   ✅ Added {ex_type.id.value}: {ex_type.name} {compatible}")
    
    session.commit()
    print("✅ Exercise types populated successfully!")

def populate_topics(session: Session):
    """Populate topics table."""
    print("🎯 Populating topics...")
    
    for topic in TOPICS.values():
        # Check if already exists
        existing = session.query(TopicDB).filter_by(id=topic.id.value).first()
        if existing:
            print(f"   ⏭️  Skipping {topic.id.value} (already exists)")
            continue
        
        db_topic = TopicDB(
            id=topic.id.value,
            name=topic.name,
            description=topic.description,
            is_active=topic.is_active,
            priority=topic.priority
        )
        session.add(db_topic)
        status = "🟢" if topic.is_active else "🔴"
        print(f"   ✅ Added {topic.id.value}: {topic.name} (Priority: {topic.priority}) {status}")
    
    session.commit()
    print("✅ Topics populated successfully!")

def populate_curriculum_structure(session: Session):
    """Populate curriculum structure table with combinations."""
    print("📊 Populating curriculum structure...")
    
    combinations = get_mvp_curriculum_matrix()
    
    for combo in combinations:
        # Check if already exists
        existing = session.query(CurriculumStructureDB).filter_by(id=combo.id).first()
        if existing:
            print(f"   ⏭️  Skipping {combo.id} (already exists)")
            continue
        
        db_combo = CurriculumStructureDB(
            id=combo.id,
            language_pair_id=combo.language_pair_id.value,
            level_id=combo.level_id.value,
            category_id=combo.category_id.value,
            exercise_type_id=combo.exercise_type_id.value,
            topic_id=combo.topic_id.value,
            generation_status=combo.generation_status,
            exercises_generated=combo.exercises_generated,
            exercises_target=combo.exercises_target,
            priority=combo.priority
        )
        session.add(db_combo)
        
        # Get human-readable names for display
        lang_pair = LANGUAGE_PAIRS[combo.language_pair_id]
        category = CONTENT_CATEGORIES[combo.category_id]
        ex_type = EXERCISE_TYPES[combo.exercise_type_id]
        topic = TOPICS[combo.topic_id]
        
        print(f"   ✅ Added {combo.id}: {lang_pair.source_name}→{lang_pair.target_name} | {category.name} | {ex_type.name} | {topic.name}")
    
    session.commit()
    print(f"✅ Curriculum structure populated successfully! ({len(combinations)} combinations)")

def print_database_summary(session: Session):
    """Print a summary of the populated database."""
    print("\n📈 DATABASE SUMMARY")
    print("=" * 60)
    
    # Count records in each table
    lang_pairs_count = session.query(LanguagePairDB).count()
    cefr_levels_count = session.query(CEFRLevelDB).count()
    categories_count = session.query(ContentCategoryDB).count()
    exercise_types_count = session.query(ExerciseTypeDB).count()
    topics_count = session.query(TopicDB).count()
    combinations_count = session.query(CurriculumStructureDB).count()
    
    print(f"🌍 Language Pairs: {lang_pairs_count}")
    print(f"📚 CEFR Levels: {cefr_levels_count}")
    print(f"📖 Content Categories: {categories_count}")
    print(f"✏️  Exercise Types: {exercise_types_count}")
    print(f"🎯 Topics: {topics_count}")
    print(f"📊 Curriculum Combinations: {combinations_count}")
    
    # Show MVP focus
    active_lang_pairs = session.query(LanguagePairDB).filter_by(is_active=True).all()
    active_categories = session.query(ContentCategoryDB).filter_by(is_active=True).all()
    active_ex_types = session.query(ExerciseTypeDB).filter_by(is_active=True).all()
    active_topics = session.query(TopicDB).filter_by(is_active=True).all()
    
    print(f"\n🎯 MVP FOCUS:")
    print(f"   Active Language Pairs: {len(active_lang_pairs)}")
    for pair in active_lang_pairs:
        print(f"     - {pair.source_name} → {pair.target_name}")
    
    print(f"   Active Categories: {len(active_categories)}")
    for cat in active_categories:
        print(f"     - {cat.name}")
    
    print(f"   Active Exercise Types: {len(active_ex_types)}")
    for ex_type in active_ex_types:
        compatible = "✅" if ex_type.whatsapp_compatible else "❌"
        print(f"     - {ex_type.name} {compatible}")
    
    print(f"   Active Topics: {len(active_topics)}")
    for topic in sorted(active_topics, key=lambda t: t.priority):
        print(f"     - {topic.name} (Priority: {topic.priority})")
    
    # Calculate total exercises needed
    total_exercises_needed = combinations_count * 20  # 20 exercises per combination
    print(f"\n🎪 CONTENT GENERATION TARGETS:")
    print(f"   Total Combinations: {combinations_count}")
    print(f"   Exercises per Combination: 20")
    print(f"   Total Exercises to Generate: {total_exercises_needed}")

def main():
    """Main function to initialize the curriculum database."""
    parser = argparse.ArgumentParser(description='Initialize curriculum database')
    parser.add_argument('--force', action='store_true', help='Drop and recreate all tables')
    parser.add_argument('--db-url', default='sqlite:///scripts/curriculum.db', help='Database URL')
    
    args = parser.parse_args()
    
    print("🎓 CURRICULUM DATABASE INITIALIZATION")
    print("=" * 60)
    
    # Create database engine
    engine = create_engine(args.db_url, echo=False)
    
    # Drop tables if force flag is set
    if args.force:
        print("🗑️  Dropping existing tables...")
        Base.metadata.drop_all(engine)
        print("✅ Tables dropped successfully!")
    
    # Create schema
    create_database_schema(engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Populate all tables
        populate_language_pairs(session)
        populate_cefr_levels(session)
        populate_content_categories(session)
        populate_exercise_types(session)
        populate_topics(session)
        populate_curriculum_structure(session)
        
        # Print summary
        print_database_summary(session)
        
        print(f"\n✅ Curriculum database initialized successfully!")
        print(f"📁 Database file: {args.db_url}")
        print(f"\nNext steps:")
        print(f"1. Create exercise schema registry")
        print(f"2. Implement schema-aware content generator")
        print(f"3. Run content generation pipeline")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
