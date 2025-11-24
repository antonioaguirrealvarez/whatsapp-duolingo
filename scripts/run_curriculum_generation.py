#!/usr/bin/env python3
"""Run Curriculum Generation Pipeline

This script executes the complete curriculum generation pipeline with
progress tracking and error handling.

Usage:
    python scripts/run_curriculum_generation.py --batch-size 10 --dry-run
    python scripts/run_curriculum_generation.py --languages es,en --levels B1
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from orchestrator.content_orchestrator import ContentOrchestrator, run_content_generation_batch
from services.curriculum.parser import get_mvp_generation_specs

def run_pipeline(args):
    """Execute the curriculum generation pipeline."""
    print("🎓 CURRICULUM GENERATION PIPELINE")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = ContentOrchestrator()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual generation")
        
        # Show queue info
        queue_info = orchestrator.get_generation_statistics()
        print(f"\n📊 Generation Queue:")
        print(f"   Total Combinations: {queue_info['total_combinations']}")
        print(f"   Pending: {queue_info['pending']}")
        print(f"   Completed: {queue_info['completed']}")
        print(f"   Failed: {queue_info['failed']}")
        print(f"   Completion Rate: {queue_info['completion_rate']:.1f}%")
        
        # Preview next batch
        preview = orchestrator.preview_next_batch(args.batch_size)
        print(f"\n🔍 Next Batch Preview ({len(preview)} combos):")
        for i, item in enumerate(preview, 1):
            print(f"   {i}. {item['id']}: {item['language_pair']} | {item['category']} | {item['exercise_type']}")
        
        print(f"\n📊 Generation Plan:")
        print(f"   Combinations: {len(preview)}")
        print(f"   Variations per combo: {args.variations}")
        print(f"   Total exercises to generate: {len(preview) * args.variations}")
        
        print(f"\n✅ Dry run completed!")
        return
    
    print(f"🚀 Starting generation batch")
    print(f"   Combinations: {args.batch_size}")
    print(f"   Variations per combo: {args.variations}")
    print(f"   Total exercises: {args.batch_size * args.variations}")
    print(f"⏰ Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Run generation batch
    results = orchestrator.orchestrate_content_generation(args.batch_size, args.variations)
    
    # Display results
    print(f"\n📊 Generation Results:")
    print(f"   Total Requested: {results.total_requested}")
    print(f"   Total Generated: {results.total_generated}")
    print(f"   Successful: {results.successful}")
    print(f"   Failed: {results.failed}")
    print(f"   Duration: {(results.end_time - results.start_time).total_seconds():.2f}s")
    
    if results.errors:
        print(f"\n❌ Errors:")
        for error in results.errors[:5]:  # Show first 5 errors
            print(f"   - {error}")
        if len(results.errors) > 5:
            print(f"   ... and {len(results.errors) - 5} more errors")
    
    if results.exercises:
        print(f"\n✅ Generated Exercises:")
        for i, exercise in enumerate(results.exercises[:3], 1):
            print(f"   {i}. {exercise.curriculum_combo_id}: {exercise.exercise_type_id}")
            print(f"      Theory: {exercise.theory[:50]}...")
            print(f"      Input: {exercise.exercise_input[:50]}...")
            print(f"      Output: {exercise.expected_output}")
        
        if len(results.exercises) > 3:
            print(f"   ... and {len(results.exercises) - 3} more exercises")
    
    # Show updated statistics
    final_stats = orchestrator.get_generation_statistics()
    print(f"\n📈 Updated Statistics:")
    print(f"   Completion Rate: {final_stats['completion_rate']:.1f}%")
    print(f"   Pending: {final_stats['pending']}")
    print(f"   Completed: {final_stats['completed']}")
    
    print(f"\n✅ Pipeline completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Run curriculum generation pipeline')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of curriculum combinations to process')
    parser.add_argument('--variations', type=int, default=10, help='Number of exercise variations per combination')
    parser.add_argument('--dry-run', action='store_true', help='Preview what will be generated without actual generation')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
