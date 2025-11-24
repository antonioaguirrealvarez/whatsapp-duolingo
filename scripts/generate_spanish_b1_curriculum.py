#!/usr/bin/env python3
"""Generate Portuguese→English B1 Curriculum with Evaluation

This script generates the complete curriculum for Portuguese→English B1 level with:
1. Row-by-row processing of curriculum combinations
2. Multiple variations with different seeds
3. LLM content generation with full context
4. Evaluator step for content and schema validation
5. Database storage of accepted exercises

Usage:
    python scripts/generate_spanish_b1_curriculum.py [--variations 10] [--dry-run] [--verbose]
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from orchestrator.content_orchestrator import ContentOrchestrator
from services.curriculum.parser import get_mvp_generation_specs
from services.curriculum.curriculum_database import ExerciseTypeID

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def filter_spanish_b1_specs(specs: List) -> List:
    """Filter specs for Spanish→English B1 combinations only."""
    filtered = []
    for spec in specs:
        if (spec.language_pair_name == 'Spanish → English' and 
            spec.level == 'B1'):
            filtered.append(spec)
    return filtered

def preview_spanish_b1_curriculum(specs: List, variations: int):
    """Preview what will be generated for Spanish→English B1."""
    print("🎓 SPANISH→ENGLISH B1 CURRICULUM PREVIEW")
    print("=" * 60)
    
    print(f"📊 Curriculum Statistics:")
    print(f"   Total combinations: {len(specs)}")
    print(f"   Variations per combo: {variations}")
    print(f"   Total exercises to generate: {len(specs) * variations}")
    
    print(f"\n📋 Exercise Type Distribution:")
    type_counts = {}
    for spec in specs:
        ex_type = spec.exercise_type
        type_counts[ex_type] = type_counts.get(ex_type, 0) + 1
    
    for ex_type, count in sorted(type_counts.items()):
        print(f"   {ex_type}: {count} combinations × {variations} = {count * variations} exercises")
    
    print(f"\n📚 Category Distribution:")
    category_counts = {}
    for spec in specs:
        category = spec.category
        category_counts[category] = category_counts.get(category, 0) + 1
    
    for category, count in sorted(category_counts.items()):
        print(f"   {category}: {count} combinations × {variations} = {count * variations} exercises")
    
    print(f"\n🌍 Topic Distribution:")
    topic_counts = {}
    for spec in specs:
        topic = spec.topic
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    for topic, count in sorted(topic_counts.items()):
        print(f"   {topic}: {count} combinations × {variations} = {count * variations} exercises")

def generate_spanish_b1_curriculum(variations: int = 10, batch_size: int = 5):
    """Generate Spanish→English B1 curriculum with evaluation."""
    print("🎓 GENERATING SPANISH→ENGLISH B1 CURRICULUM")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = ContentOrchestrator()
    
    # Get Spanish→English B1 specs
    all_specs = get_mvp_generation_specs()
    spanish_b1_specs = filter_spanish_b1_specs(all_specs)
    
    print(f"📋 Found {len(spanish_b1_specs)} Spanish→English B1 combinations")
    print(f"🔄 Generating {variations} variations per combination")
    print(f"🎯 Total exercises to generate: {len(spanish_b1_specs) * variations}")
    print(f"⏰ Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Record start time
    start_time = datetime.utcnow()
    
    # Track generation statistics
    total_combinations = len(spanish_b1_specs)
    processed_combinations = 0
    accepted_exercises = 0
    rejected_exercises = 0
    
    # Process in batches
    for i in range(0, total_combinations, batch_size):
        batch_specs = spanish_b1_specs[i:i + batch_size]
        
        print(f"\n📦 Processing batch {i//batch_size + 1}/{(total_combinations + batch_size - 1)//batch_size}")
        print(f"   Combinations: {len(batch_specs)} ({i+1}-{min(i+batch_size, total_combinations)})")
        
        # Generate exercises for this batch
        for spec in batch_specs:
            try:
                print(f"\n🔄 Processing {spec.id}: {spec.category} | {spec.exercise_type} | {spec.topic}")
                
                # Mark as in progress
                orchestrator.curriculum_parser.update_generation_status(spec.id, "in_progress")
                
                # Generate variations with evaluation
                combo_accepted = 0
                combo_rejected = 0
                
                for variation_num in range(variations):
                    try:
                        # Get schema for this exercise type
                        schema = orchestrator.get_schema_for_exercise_type(spec.exercise_type_id)
                        
                        # Generate exercise with evaluation
                        exercise = orchestrator.generate_exercise_with_context(
                            spec, schema, variation_num=variation_num
                        )
                        
                        if exercise:
                            combo_accepted += 1
                            accepted_exercises += 1
                        else:
                            combo_rejected += 1
                            rejected_exercises += 1
                            
                    except Exception as e:
                        print(f"   ❌ Error generating variation {variation_num}: {e}")
                        combo_rejected += 1
                        rejected_exercises += 1
                
                # Update status based on results
                if combo_accepted > 0:
                    orchestrator.curriculum_parser.update_generation_status(
                        spec.id, "completed", combo_accepted
                    )
                    print(f"   ✅ Generated {combo_accepted}/{variations} exercises for {spec.id}")
                else:
                    orchestrator.curriculum_parser.update_generation_status(
                        spec.id, "failed", 0
                    )
                    print(f"   ❌ Failed to generate any exercises for {spec.id}")
                
                processed_combinations += 1
                
                # Progress update
                progress = (processed_combinations / total_combinations) * 100
                print(f"   📊 Progress: {processed_combinations}/{total_combinations} ({progress:.1f}%)")
                print(f"   📈 Accepted: {accepted_exercises} | Rejected: {rejected_exercises}")
                
            except Exception as e:
                print(f"   ❌ Error processing {spec.id}: {e}")
                orchestrator.curriculum_parser.update_generation_status(spec.id, "failed", 0)
                processed_combinations += 1
    
    # Final statistics
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n" + "=" * 60)
    print("🎯 GENERATION COMPLETE")
    print("=" * 60)
    
    print(f"📊 Final Statistics:")
    print(f"   Combinations processed: {processed_combinations}/{total_combinations}")
    print(f"   Exercises accepted: {accepted_exercises}")
    print(f"   Exercises rejected: {rejected_exercises}")
    print(f"   Acceptance rate: {(accepted_exercises/(accepted_exercises + rejected_exercises)*100):.1f}%" if (accepted_exercises + rejected_exercises) > 0 else "   Acceptance rate: N/A")
    print(f"   Duration: {duration:.2f} seconds")
    
    # Get database statistics
    db_stats = orchestrator.exercise_repo.get_exercise_statistics()
    print(f"   Total exercises in database: {db_stats.get('total_exercises', 0)}")
    
    # Get generation statistics
    gen_stats = orchestrator.get_generation_statistics()
    print(f"   Curriculum completion: {gen_stats['completed']}/{gen_stats['total_combinations']} combinations")
    
    return accepted_exercises, rejected_exercises

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Generate Portuguese→English B1 curriculum with evaluation')
    parser.add_argument('--variations', type=int, default=2, help='Number of variations per combination (default: 2)')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size for processing')
    parser.add_argument('--dry-run', action='store_true', help='Preview what will be generated without actual generation')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--resume', action='store_true', help='Resume from previous run (skip completed combinations)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Get Spanish→English B1 specs
    all_specs = get_mvp_generation_specs()
    spanish_b1_specs = filter_spanish_b1_specs(all_specs)
    
    if not spanish_b1_specs:
        print("❌ No Spanish→English B1 combinations found in curriculum")
        return 1
    
    # Filter out completed combinations if resuming
    if args.resume:
        orchestrator = ContentOrchestrator()
        completed_specs = []
        for spec in spanish_b1_specs:
            stats = orchestrator.curriculum_parser.get_generation_status(spec.id)
            if stats.get('status') == 'completed':
                completed_specs.append(spec)
        
        if completed_specs:
            print(f"🔄 Resuming: Skipping {len(completed_specs)} already completed combinations")
            spanish_b1_specs = [spec for spec in spanish_b1_specs if spec not in completed_specs]
            
            if not spanish_b1_specs:
                print("✅ All combinations already completed!")
                return 0
    
    if args.dry_run:
        preview_spanish_b1_curriculum(spanish_b1_specs, args.variations)
        print(f"\n✅ Dry run completed! Ready to generate {len(spanish_b1_specs) * args.variations} exercises.")
        return 0
    
    try:
        # Generate curriculum
        accepted, rejected = generate_spanish_b1_curriculum(
            variations=args.variations,
            batch_size=args.batch_size
        )
        
        if accepted > 0:
            print(f"\n🎉 Successfully generated {accepted} exercises for Spanish→English B1!")
            print("📚 Curriculum generation with evaluation completed!")
            return 0
        else:
            print(f"\n❌ No exercises were accepted during generation.")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Generation interrupted by user")
        print("💡 Use --resume to continue from where you left off")
        return 1
    except Exception as e:
        print(f"\n❌ Generation failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
