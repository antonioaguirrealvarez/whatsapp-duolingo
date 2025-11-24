#!/usr/bin/env python3
"""Initialize Exercise Schemas in Database

This script creates and populates the exercise_schemas table with
the 4-field structure specifications for each exercise type.

Usage:
    python scripts/init_exercise_schemas.py
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def create_exercise_schemas_table(engine):
    """Create exercise_schemas table."""
    print("🏗️  Creating exercise_schemas table...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS exercise_schemas (
        id VARCHAR(20) PRIMARY KEY,
        exercise_type VARCHAR(50) NOT NULL,
        field_theory_required BOOLEAN DEFAULT TRUE,
        field_theory_min_length INTEGER DEFAULT 500,
        field_theory_max_length INTEGER DEFAULT 2000,
        field_theory_description TEXT,
        field_introduction_required BOOLEAN DEFAULT TRUE,
        field_introduction_min_length INTEGER DEFAULT 50,
        field_introduction_max_length INTEGER DEFAULT 500,
        field_introduction_description TEXT,
        field_input_required BOOLEAN DEFAULT TRUE,
        field_input_min_length INTEGER DEFAULT 50,
        field_input_max_length INTEGER DEFAULT 1000,
        field_input_description TEXT,
        field_input_format TEXT,
        field_output_required BOOLEAN DEFAULT TRUE,
        field_output_min_length INTEGER DEFAULT 3,
        field_output_max_length INTEGER DEFAULT 500,
        field_output_description TEXT,
        field_output_format TEXT,
        validation_rules TEXT,
        example_theory TEXT,
        example_introduction TEXT,
        example_input TEXT,
        example_output TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("✅ Exercise schemas table created successfully!")

def populate_exercise_schemas(session):
    """Populate exercise schemas with 4-field structure."""
    print("📝 Populating exercise schemas...")
    
    schemas = [
        {
            'id': 'EX_MCQ',
            'exercise_type': 'multiple_choice',
            'field_theory_description': 'Concept explanation with contextual examples',
            'field_introduction_description': 'Instructions for selecting from options',
            'field_input_description': 'Sentence with blank followed by numbered options',
            'field_input_format': 'Sentence with ___ followed by [1] Option1 [2] Option2 [3] Option3',
            'field_output_description': 'Option number or the full correct phrase',
            'field_output_format': 'Number (1, 2, 3) or complete sentence',
            'validation_rules': 'Options must be numbered 1-3, only one correct answer',
            'example_theory': 'Spanish articles must agree in gender with nouns. "El" (masculine) vs "La" (feminine).',
            'example_introduction': 'Choose the correct option that best completes the sentence.',
            'example_input': '___ libro es interesante. [1] El [2] La [3] Los',
            'example_output': '1'
        },
        {
            'id': 'EX_FILL',
            'exercise_type': 'fill_blank',
            'field_theory_description': 'Grammar rule explanation or vocabulary definitions with examples',
            'field_introduction_description': 'Instructions for filling blanks',
            'field_input_description': 'Sentence with missing word marked by underscores',
            'field_input_format': 'Sentence with ___ representing missing word',
            'field_output_description': 'Single word or phrase that fills the blank',
            'field_output_format': 'Single word or short phrase',
            'validation_rules': 'Underscores represent missing word, answer must fit context',
            'example_theory': 'In Spanish, the verb "ser" is used for permanent characteristics. Example: "Yo ___ estudiante" → "Yo soy estudiante".',
            'example_introduction': 'Fill in the blank with the correct word that best completes the sentence.',
            'example_input': 'Mi hermana ___ muy inteligente.',
            'example_output': 'es'
        },
        {
            'id': 'EX_ROLEPLAY',
            'exercise_type': 'roleplay',
            'field_theory_description': 'Cultural context and functional language patterns',
            'field_introduction_description': 'Scenario setup and role description',
            'field_input_description': 'Scenario description with context',
            'field_input_format': 'Scenario description with dialogue prompt',
            'field_output_description': 'Appropriate response in target language',
            'field_output_format': 'Complete response in target language',
            'validation_rules': 'Response must be culturally appropriate and in target language',
            'example_theory': 'When ordering food in Spanish, use "Me gustaría" for polite requests. Common phrases: "¿Qué recomienda?"',
            'example_introduction': 'You are at a restaurant in Madrid. Play the role of a customer ordering lunch. Respond to the waiter\'s question.',
            'example_input': 'Camarero: "¿Qué desea tomar?" (Waiter: "What would you like to order?")',
            'example_output': 'Me gustaría una paella, por favor.'
        },
        {
            'id': 'EX_TRANS',
            'exercise_type': 'translation',
            'field_theory_description': 'Translation strategies and common pitfalls',
            'field_introduction_description': 'Translation instructions',
            'field_input_description': 'Source language sentence',
            'field_input_format': 'Complete sentence in source language',
            'field_output_description': 'Accurate translation in target language',
            'field_output_format': 'Complete sentence in target language',
            'validation_rules': 'Translation must maintain meaning and be grammatically correct',
            'example_theory': 'False cognates: "embarazada" means "pregnant", not "embarrassed". Always consider context.',
            'example_introduction': 'Translate the following sentence from Spanish to English.',
            'example_input': 'Ayer fui al mercado.',
            'example_output': 'Yesterday I went to the market.'
        },
        {
            'id': 'EX_ERROR',
            'exercise_type': 'error_identification',
            'field_theory_description': 'Common error patterns and correction rules',
            'field_introduction_description': 'Error-finding instructions',
            'field_input_description': 'Sentence containing an error',
            'field_input_format': 'Sentence with grammatical or vocabulary error',
            'field_output_description': 'Corrected sentence',
            'field_output_format': 'Complete corrected sentence',
            'validation_rules': 'Output must fix the error in the input',
            'example_theory': 'Ser vs Estar: Use "ser" for permanent states, "estar" for temporary conditions. "Estoy cansado" (temporary), "Soy profesor" (permanent).',
            'example_introduction': 'Find and correct the error in the following sentence.',
            'example_input': 'Yo estoy profesor.',
            'example_output': 'Yo soy profesor.'
        },
        {
            'id': 'EX_OPEN',
            'exercise_type': 'open_response',
            'field_theory_description': 'Communication strategies and response patterns',
            'field_introduction_description': 'Open-ended response instructions',
            'field_input_description': 'Open-ended question',
            'field_input_format': 'Question requiring personal or creative response',
            'field_output_description': 'Complete personal response',
            'field_output_format': 'Complete sentence or multiple sentences',
            'validation_rules': 'Response must be relevant and in target language',
            'example_theory': 'In Spanish conversations, it\'s common to use diminutives like "-ito" for politeness: "un momentito".',
            'example_introduction': 'Respond to the following question in a complete sentence.',
            'example_input': '¿Cómo te llamas y de dónde eres?',
            'example_output': 'Me llamo Carlos y soy de México.'
        }
    ]
    
    for schema_data in schemas:
        # Check if already exists
        existing = session.execute(text("SELECT id FROM exercise_schemas WHERE id = :id"), 
                                 {'id': schema_data['id']}).fetchone()
        
        if existing:
            print(f"   ⏭️  Skipping {schema_data['id']} (already exists)")
            continue
        
        # Insert new schema
        insert_sql = """
        INSERT INTO exercise_schemas (
            id, exercise_type, field_theory_description, field_introduction_description,
            field_input_description, field_input_format, field_output_description, field_output_format,
            validation_rules, example_theory, example_introduction, example_input, example_output
        ) VALUES (
            :id, :exercise_type, :field_theory_description, :field_introduction_description,
            :field_input_description, :field_input_format, :field_output_description, :field_output_format,
            :validation_rules, :example_theory, :example_introduction, :example_input, :example_output
        )
        """
        
        session.execute(text(insert_sql), schema_data)
        print(f"   ✅ Added {schema_data['id']}: {schema_data['exercise_type']}")
    
    session.commit()
    print("✅ Exercise schemas populated successfully!")

def main():
    """Main function to initialize exercise schemas."""
    print("🎓 EXERCISE SCHEMAS INITIALIZATION")
    print("=" * 60)
    
    # Create database engine
    engine = create_engine("sqlite:///scripts/curriculum.db", echo=False)
    
    # Create table
    create_exercise_schemas_table(engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Populate schemas
        populate_exercise_schemas(session)
        
        # Show summary
        result = session.execute(text("SELECT id, exercise_type FROM exercise_schemas ORDER BY id"))
        schemas = result.fetchall()
        
        print(f"\n📊 Exercise Schemas Summary:")
        print(f"   Total schemas: {len(schemas)}")
        for schema in schemas:
            print(f"   {schema.id}: {schema.exercise_type}")
        
        print(f"\n✅ Exercise schemas initialized successfully!")
        print(f"📁 Database: scripts/curriculum.db")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
