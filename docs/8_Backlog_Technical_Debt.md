# Technical Debt Backlog

This document tracks technical debt items organized by project phases and subphases for systematic resolution.

## Phase 1: Foundation & Infrastructure

### 1.1 Database Architecture
- **Priority**: Medium
- **Status**: Pending

#### Items:
- **Database Location**: Revisit whether `curriculum.db` should be in `scripts/` or a dedicated `data/` directory
  - **Current Location**: `scripts/curriculum.db`
  - **Proposed**: `data/curriculum.db` 
  - **Files to Change**:
    - `src/core/config.py` - Update database URL paths
    - `scripts/init_curriculum_database.py` - Update database path
    - `src/orchestrator/content_orchestrator.py` - Update database URL
  - **Example**: 
    ```python
    # Current
    database_url: str = "sqlite:///scripts/curriculum.db"
    # Proposed
    database_url: str = "sqlite:///data/curriculum.db"
    ```

### 1.2 Core Configuration
- **Priority**: Low
- **Status**: Pending

#### Items:
- **Environment Configuration**: Standardize database paths across environments
  - **Files to Change**: `src/core/config.py`
  - **Example**: Add `DATABASE_PATH` configuration option

## Phase 2: Content Generation & Management

### 2.3 Content Generation Pipeline ⭐ **HIGH PRIORITY**
- **Priority**: High
- **Status**: Active Development

#### Items:

##### 1. Exercise Type Integration in LLM Generation
- **Description**: Exercise type (grammar, vocabulary, etc.) is not explicitly passed to LLM for exercise creation
- **Impact**: LLM may not optimize content for specific exercise types
- **Files to Change**:
  - `src/services/llm/schema_aware_generator.py` - `build_context_aware_prompt()` method
  - `src/orchestrator/content_orchestrator.py` - `generate_exercise_with_context()` method
- **Example Implementation**:
  ```python
  # Current prompt lacks exercise type context
  prompt = f"""Generate 1 exercise for the following specifications:
  - Source Language: {spec.language_pair[0]}
  - Target Language: {spec.language_pair[1]}
  - Difficulty Level: {spec.level}
  - Topic: {spec.topic}"""
  
  # Enhanced prompt with exercise type
  prompt = f"""Generate 1 exercise for the following specifications:
  - Source Language: {spec.language_pair[0]}
  - Target Language: {spec.language_pair[1]}
  - Difficulty Level: {spec.level}
  - Exercise Type: {spec.exercise_type}  # NEW: Explicit exercise type
  - Topic: {spec.topic}
  
  Exercise Type Guidelines:
  - For "Grammar": Focus on grammatical structures, verb conjugations, sentence patterns
  - For "Vocabulary": Focus on word meanings, synonyms, context usage
  - For "Roleplay": Focus on conversational scenarios, dialogue patterns"""
  ```

##### 2. Exercise Type Storage in Database
- **Description**: Exercise type is not stored in the exercises table
- **Impact**: Cannot filter or analyze exercises by type later
- **Files to Change**:
  - `src/data/repositories/exercise_repo.py` - `save_exercise_from_orchestrator()` method
  - `src/data/models.py` - Add `exercise_type` field to Exercise model
- **Example Implementation**:
  ```python
  # Current save function
  def save_exercise_from_orchestrator(exercise: GeneratedExercise, curriculum_combo_id: str):
      # ... existing code ...
      new_exercise = Exercise(
          # ... existing fields ...
          # Missing exercise_type field
      )
  
  # Enhanced save function
  def save_exercise_from_orchestrator(exercise: GeneratedExercise, curriculum_combo_id: str):
      # ... existing code ...
      new_exercise = Exercise(
          # ... existing fields ...
          exercise_type=exercise.exercise_type_id.value,  # NEW: Store exercise type
      )
  ```

##### 3. Enhanced LLM Prompt with Examples
- **Description**: Current prompts lack specific examples and field explanations
- **Impact**: Lower quality exercise generation, inconsistent formats
- **Files to Change**:
  - `src/services/llm/schema_aware_generator.py` - `build_context_aware_prompt()` method
- **Example Implementation**:
  ```python
  def build_context_aware_prompt(self, generation_spec, exercise_schema, variation_num: int = 0):
      prompt = f"""You are an expert language learning content creator. Generate educational exercises for language learners.

  Generate 1 exercise for the following specifications:
  - Source Language: {generation_spec.language_pair[0]}
  - Target Language: {generation_spec.language_pair[1]}
  - Difficulty Level: {generation_spec.level} (CEFR)
  - Exercise Type: {generation_spec.exercise_type}
  - Topic: {generation_spec.topic}
  - Content Category: {generation_spec.category}

  ## Exercise Type: {generation_spec.exercise_type}
  ## Field Descriptions:
  - **theory**: Clear explanation of the concept with examples (2-3 sentences)
  - **exercise_introduction**: Simple instructions for the learner (1-2 sentences)
  - **exercise_input**: The actual exercise content following the format specified
  - **expected_output**: The correct answer or expected response

  ## Examples for {generation_spec.exercise_type}:
  {self._get_examples_for_exercise_type(generation_spec.exercise_type)}

  ## Schema Requirements:
  - Theory Description: {exercise_schema.field_theory_description}
  - Input Format: {exercise_schema.field_input_format}
  - Output Format: {exercise_schema.field_output_format}

  ## Output Format:
  Return a JSON object with exactly these fields:
  {{
      "theory": "...",
      "exercise_introduction": "...",
      "exercise_input": "...",
      "expected_output": "..."
  }}

  VARIATION SEED: {variation_num}
  Generate a completely different exercise than previous variations."""
      
      return prompt
  ```

##### 4. Enhanced Post-Generation Validators
- **Description**: Need more comprehensive validation after exercise creation
- **Impact**: Poor quality exercises may pass current validation
- **Files to Change**:
  - `src/services/validation/exercise_evaluator.py` - Add new validation methods
  - `src/orchestrator/content_orchestrator.py` - Enhanced validation pipeline
- **Example Implementation**:
  ```python
  class ExerciseValidator:
      def validate_exercise_comprehensive(self, exercise_data, exercise_spec):
          """Comprehensive validation with multiple checks"""
          validations = {
              'language_validation': self._validate_languages(exercise_data, exercise_spec),
              'format_validation': self._validate_output_format(exercise_data),
              'content_validation': self._validate_content_quality(exercise_data),
              'schema_validation': self._validate_schema_compliance(exercise_data)
          }
          return validations
      
      def _validate_languages(self, exercise_data, exercise_spec):
          """Ensure base and learning languages are correctly used"""
          issues = []
          # Check that input contains source language
          # Check that expected output is in target language
          # Check for language mixing errors
          return issues
      
      def _validate_output_format(self, exercise_data):
          """Ensure expected output format is clean and parseable"""
          issues = []
          expected_output = exercise_data.get('expected_output', '')
          
          # Check for common formatting issues
          if expected_output.startswith('"') and expected_output.endswith('"'):
              issues.append("Expected output should not be in quotes")
          
          if expected_output.strip() != expected_output:
              issues.append("Expected output has leading/trailing whitespace")
              
          return issues
  ```

##### 5. Parallel Dataset Generation Optimization
- **Description**: Current generation is sequential; could be parallelized for better performance
- **Impact**: Faster curriculum generation for large datasets
- **Files to Change**:
  - `src/orchestrator/content_orchestrator.py` - Add parallel processing
  - `scripts/generate_spanish_b1_curriculum.py` - Add parallel execution option
- **Example Implementation**:
  ```python
  import asyncio
  from concurrent.futures import ThreadPoolExecutor, as_completed
  
  class ContentOrchestrator:
      def orchestrate_content_generation_parallel(self, batch_size: int = 10, 
                                                variations_per_combo: int = 2,
                                                max_workers: int = 4):
          """Parallel generation with multiple workers"""
          
          with ThreadPoolExecutor(max_workers=max_workers) as executor:
              # Submit all generation tasks
              futures = []
              for spec in pending_specs:
                  for variation_num in range(variations_per_combo):
                      future = executor.submit(
                          self._generate_and_save_exercise,
                          spec, variation_num
                      )
                      futures.append(future)
              
              # Process results as they complete
              for future in as_completed(futures):
                  try:
                      result = future.result()
                      # Handle result
                  except Exception as e:
                      # Handle error
                      pass
  
