#!/usr/bin/env python3
"""View Curriculum Database Contents

This script displays the contents of the curriculum database in a readable format.

Usage:
    python scripts/view_curriculum_database.py [--table TABLE_NAME]
"""

import sys
import os
import argparse
from typing import List

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def view_language_pairs(session):
    """View language pairs table."""
    print("\n🌍 LANGUAGE PAIRS")
    print("=" * 80)
    
    result = session.execute(text("""
        SELECT id, source_lang, target_lang, source_name, target_name, 
               is_active, priority 
        FROM language_pairs 
        ORDER BY priority, id
    """))
    
    print(f"{'ID':<12} {'Source':<8} {'Target':<8} {'Pair Name':<30} {'Active':<8} {'Priority':<8}")
    print("-" * 80)
    
    for row in result:
        status = "✅" if row.is_active else "❌"
        pair_name = f"{row.source_name} → {row.target_name}"
        print(f"{row.id:<12} {row.source_lang:<8} {row.target_lang:<8} {pair_name:<30} {status:<8} {row.priority:<8}")

def view_curriculum_combinations(session, limit=20):
    """View curriculum combinations table."""
    print(f"\n📊 CURRICULUM COMBINATIONS (Top {limit})")
    print("=" * 120)
    
    result = session.execute(text(f"""
        SELECT cs.id, lp.source_name, lp.target_name, cl.name as level,
               cc.name as category, et.name as exercise_type, t.name as topic,
               cs.generation_status, cs.exercises_target, cs.priority
        FROM curriculum_structure cs
        JOIN language_pairs lp ON cs.language_pair_id = lp.id
        JOIN cefr_levels cl ON cs.level_id = cl.id
        JOIN content_categories cc ON cs.category_id = cc.id
        JOIN exercise_types et ON cs.exercise_type_id = et.id
        JOIN topics t ON cs.topic_id = t.id
        WHERE lp.is_active = 1 AND cc.is_active = 1 AND et.is_active = 1
        ORDER BY cs.priority, cs.id
        LIMIT {limit}
    """))
    
    print(f"{'ID':<10} {'Language':<20} {'Category':<15} {'Exercise':<15} {'Topic':<20} {'Status':<12} {'Target':<8}")
    print("-" * 120)
    
    for row in result:
        lang_pair = f"{row.source_name[:8]}→{row.target_name[:8]}"
        status_icon = "⏳" if row.generation_status == "pending" else "✅" if row.generation_status == "completed" else "❌"
        print(f"{row.id:<10} {lang_pair:<20} {row.category:<15} {row.exercise_type:<15} {row.topic[:20]:<20} {status_icon:<12} {row.exercises_target:<8}")

def view_generation_stats(session):
    """View generation statistics."""
    print("\n📈 GENERATION STATISTICS")
    print("=" * 60)
    
    # Overall stats
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
    
    row = result.fetchone()
    
    print(f"Total Combinations: {row.total_combinations}")
    print(f"Completed: {row.completed} ✅")
    print(f"Pending: {row.pending} ⏳")
    print(f"In Progress: {row.in_progress} 🔄")
    print(f"Failed: {row.failed} ❌")
    print(f"Target Exercises: {row.total_target_exercises}")
    print(f"Generated Exercises: {row.total_generated_exercises}")
    
    if row.total_target_exercises > 0:
        completion_rate = (row.total_generated_exercises / row.total_target_exercises) * 100
        print(f"Completion Rate: {completion_rate:.1f}%")

def view_by_language_pair(session):
    """View combinations grouped by language pair."""
    print("\n🌍 COMBINATIONS BY LANGUAGE PAIR")
    print("=" * 80)
    
    result = session.execute(text("""
        SELECT lp.source_name, lp.target_name,
               COUNT(*) as combinations,
               SUM(exercises_target) as target_exercises,
               SUM(exercises_generated) as generated_exercises
        FROM curriculum_structure cs
        JOIN language_pairs lp ON cs.language_pair_id = lp.id
        WHERE lp.is_active = 1
        GROUP BY lp.id, lp.source_name, lp.target_name
        ORDER BY combinations DESC
    """))
    
    print(f"{'Language Pair':<25} {'Combinations':<12} {'Target':<10} {'Generated':<10} {'Progress':<10}")
    print("-" * 80)
    
    for row in result:
        lang_pair = f"{row.source_name} → {row.target_name}"
        progress = 0
        if row.target_exercises > 0:
            progress = (row.generated_exercises / row.target_exercises) * 100
        progress_bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
        
        print(f"{lang_pair:<25} {row.combinations:<12} {row.target_exercises:<10} {row.generated_exercises:<10} {progress_bar:<10} {progress:.1f}%")

def view_by_category(session):
    """View combinations grouped by content category."""
    print("\n📚 COMBINATIONS BY CONTENT CATEGORY")
    print("=" * 80)
    
    result = session.execute(text("""
        SELECT cc.name,
               COUNT(*) as combinations,
               SUM(exercises_target) as target_exercises,
               SUM(exercises_generated) as generated_exercises
        FROM curriculum_structure cs
        JOIN content_categories cc ON cs.category_id = cc.id
        WHERE cc.is_active = 1
        GROUP BY cc.id, cc.name
        ORDER BY combinations DESC
    """))
    
    print(f"{'Category':<20} {'Combinations':<12} {'Target':<10} {'Generated':<10} {'Progress':<10}")
    print("-" * 80)
    
    for row in result:
        progress = 0
        if row.target_exercises > 0:
            progress = (row.generated_exercises / row.target_exercises) * 100
        progress_bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
        
        print(f"{row.name:<20} {row.combinations:<12} {row.target_exercises:<10} {row.generated_exercises:<10} {progress_bar:<10} {progress:.1f}%")

def view_exercise_types(session):
    """View exercise types with WhatsApp compatibility."""
    print("\n✏️  EXERCISE TYPES")
    print("=" * 80)
    
    result = session.execute(text("""
        SELECT id, name, is_active, requires_audio, whatsapp_compatible
        FROM exercise_types
        ORDER BY id
    """))
    
    print(f"{'ID':<12} {'Name':<20} {'Active':<8} {'Audio':<8} {'WhatsApp':<10}")
    print("-" * 80)
    
    for row in result:
        active = "✅" if row.is_active else "❌"
        audio = "🔊" if row.requires_audio else "📝"
        whatsapp = "✅" if row.whatsapp_compatible else "❌"
        print(f"{row.id:<12} {row.name:<20} {active:<8} {audio:<8} {whatsapp:<10}")

def main():
    """Main function to view curriculum database."""
    parser = argparse.ArgumentParser(description='View curriculum database contents')
    parser.add_argument('--table', choices=['language_pairs', 'combinations', 'stats', 'by_language', 'by_category', 'exercise_types'], 
                       help='Specific table to view')
    parser.add_argument('--limit', type=int, default=20, help='Limit for combinations display')
    parser.add_argument('--db-url', default='sqlite:///scripts/curriculum.db', help='Database URL')
    
    args = parser.parse_args()
    
    print("🎓 CURRICULUM DATABASE VIEWER")
    print("=" * 60)
    
    # Create database engine
    engine = create_engine(args.db_url, echo=False)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        if args.table == 'language_pairs' or args.table is None:
            view_language_pairs(session)
        
        if args.table == 'combinations' or args.table is None:
            view_curriculum_combinations(session, args.limit)
        
        if args.table == 'stats' or args.table is None:
            view_generation_stats(session)
        
        if args.table == 'by_language' or args.table is None:
            view_by_language_pair(session)
        
        if args.table == 'by_category' or args.table is None:
            view_by_category(session)
        
        if args.table == 'exercise_types' or args.table is None:
            view_exercise_types(session)
        
        print(f"\n✅ Database view completed!")
        print(f"📁 Database file: {args.db_url}")
        
    except Exception as e:
        print(f"❌ Error viewing database: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
