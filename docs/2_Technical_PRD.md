### Recommended Action
Please update `docs/2_Technical_PRD.md` with the following content:

```markdown:docs/2_Technical_PRD.md
# 🛠️ TECHNICAL PRODUCT REQUIREMENTS DOCUMENT (Technical PRD)
**Project:** WhatsApp-First AI Language Tutor
**Version:** 2.0
**Status:** Draft

---

## 1. Technical Stack & Architecture
### 1.1 High-Level Architecture
The system operates as an event-driven, state-aware application. It distinguishes between **Synchronous Operations** (responding to a user message in real-time) and **Asynchronous Operations** (generating curriculum, evaluating sessions, clustering users).

*   **Interface Layer:** WhatsApp API (via Twilio for initial implementation, with scaffoldings for future migration to WhatsApp Business API).
*   **Orchestrator Layer (The Core):** A Python-based event bus that coordinates User State, DB I/O, and LLM calls.
*   **Intelligence Layer:** LangChain + LangGraph for agentic flows; LangSmith for observability/judging.
*   **Growth & Business Layer:** Dedicates modules for A/B testing, Stripe monetization, and user segmentation.

### 1.2 Core Technology Stack
*   **Backend:** Python 3.11+
    *   **Web Framework:** FastAPI (high performance, async support).
    *   **Task Queue:** Celery + Redis (for async curriculum generation & heavy orchestration).
*   **LLM Infrastructure:**
    *   **Orchestration:** LangChain v1 (Agents) & LangGraph (Stateful flows).
    *   **Observability:** LangSmith (Traces, datasets, evaluators).
    *   **Models:** OpenAI (`gpt-4o-mini` for chat, `gpt-4o` for complex judging/generation).
    *   **Voice:** ElevenLabs for TTS and STT, and voice information extraction.
*   **Frontend (Landing Page):** Next.js 14 + TailwindCSS.

---

## 2. File & Folder Structure
Expanded to reflect the complexity of the Orchestrator and LLM services.

```text
src/
├── api/
│   ├── routes/
│   │   ├── webhook_whatsapp.py  # Ingress for messages
│   │   ├── webhook_stripe.py    # Ingress for payments
│   │   └── cron_triggers.py     # Internal triggers (daily nudges)
├── orchestrator/                # THE NERVOUS SYSTEM
│   ├── core.py                  # Main Event Loop
│   ├── router.py                # Intent classification & routing
│   ├── session_manager.py       # User context retrieval/storage
│   └── scheduler.py             # Macro-level scheduling (cron wrappers)
├── services/
│   ├── llm/                     # THE BRAIN
│   │   ├── gateway.py           # Unified Model Interface (Sync/Async)
│   │   ├── prompts/             # Jinja2 templates for prompts
│   │   ├── agents/
│   │   │   ├── tutor_agent.py   # The conversational partner
│   │   │   └── content_agent.py # The curriculum generator
│   │   ├── evals/
│   │   │   ├── judge_correctness.py
│   │   │   └── judge_tone.py
│   │   └── langsmith_client.py  # Tracing setup
│   ├── whatsapp/
│   │   ├── io.py                # Send/Receive abstractions
│   │   └── templates.py         # Message formats (Lists, Buttons)
│   ├── business/
│   │   ├── monetization.py      # Stripe logic & Limits enforcement
│   │   └── analytics.py         # Usage tracking
│   └── growth/
│   │   ├── ab_testing.py        # Experiment assignment
│   │   └── clustering.py        # User segmentation logic
└── data/
    ├── repositories/            # DB Access Patterns
    └── cache/                   # Redis helpers
```

---

## 3. Core Modules & Functional Specs

### 3.1 The Orchestrator (Central Nervous System)
This module controls the flow of information. It does not "think" (LLM does that) or "store" (DB does that); it coordinates.

*   **File:** `src/orchestrator/core.py`
    *   **Function:** `handle_user_event(event: WhatsAppEvent)`
        *   *Logic:* The entry point.
        1.  Calls `session_manager.load_context(user_id)`.
        2.  Calls `router.decide_next_action(context, event)`.
        3.  Executes the action (e.g., `call_llm` or `send_static_message`).
        4.  Updates state via `session_manager.save_state()`.
*   **File:** `src/orchestrator/router.py`
    *   **Function:** `route_intent(user_input: str, state: UserState) -> Action`
        *   *Logic:* Uses a lightweight LLM router or Regex (for commands) to determine if user is answering a question, asking for help, or trying to pay.
        *   *Params:* `current_mode` (e.g., "in_quiz"), `last_bot_message_id`.
*   **File:** `src/orchestrator/session_manager.py`
    *   **Function:** `enrich_context(user_id)`
        *   *Logic:* Aggregates data from DB (Level, Name), Business (Is Paid?), and History (Last 5 messages) into a single Context Object for the LLM.
*   **File:** `src/orchestrator/scheduler.py` (Macro Level)
    *   **Function:** `trigger_daily_engagement()`
        *   *Logic:* Runs a query for users who haven't practiced in 23 hours. Queues individual "Nudge" jobs.

### 3.2 The Brain (LLM Gateway & Agents)
Handles all cognitive tasks.

*   **File:** `src/services/llm/gateway.py`
    *   **Function:** `ainvoke(prompt, model_type='fast')`
        *   *Logic:* Wraps LangChain's `ChatOpenAI`. Handles retries, fallback models, and distinct API keys.
    *   **Function:** `get_structured_output(schema: BaseModel)`
        *   *Logic:* Forces JSON output (e.g., for extracting "User Mistake" and "Correction").
*   **File:** `src/services/llm/agents/tutor_agent.py` (Sync)
    *   **Function:** `generate_reply(user_input, history, persona)`
        *   *Logic:* The main chat loop. Injects the "Viral Persona" prompt.
        *   *Returns:* Text response + Suggested Reply Buttons.
*   **File:** `src/services/llm/agents/content_agent.py` (Async)
    *   **Function:** `batch_generate_exercises(topic, level, count=50)`
    *   **Logic:** Heavy background job. Generates curriculum content to be stored in DB.
    *   **Note:** Legacy implementation - see Advanced Content Factory for schema-driven approach.

### 3.3 Advanced Content Factory (Schema-Driven Generation)
Multi-layered content generation system with curriculum parsing, schema mapping, and structured validation.

#### 3.3.1 Curriculum Structure Management
*   **File:** `src/services/curriculum/parser.py`
    *   **Functions:** `parse_curriculum_from_database()`, `extract_generation_specs()`, `get_pending_combinations()`, `update_generation_status()`
    *   **Logic:** Query curriculum database → Convert to generation specs → Track generation status
    *   **Returns:** GenerationSpec objects ready for content generation pipeline

*   **File:** `src/services/curriculum/curriculum_database.py`
    *   **Classes:** `CurriculumCombination`, `GenerationSpec`, standardized ID enums
    *   **Storage:** `scripts/curriculum.db` SQLite database with 54 MVP combinations
    *   **Standardized IDs:** LANG_001, CAT_VOCAB, EX_MCQ, TOPIC_DAILY, COMBO_001

#### 3.3.2 Exercise Schema Registry
*   **File:** `src/services/schema/exercise_schema.py`
    *   **Function:** `get_schema_for_exercise_type(exercise_type: str) -> ExerciseSchema`
    *   **Logic:** Retrieves JSON schema and validation rules for specific exercise types
    *   **Returns:** ExerciseSchema with required fields, field types, constraints

*   **File:** `src/services/schema/registry.py`
    *   **Classes:** `ExerciseSchema`, `FieldDefinition`, `ValidationRule`
    *   **Logic:** Schema registry mapping exercise types to 4-field structure (theory, introduction, input, output)

#### 3.3.3 Schema-Aware Content Generation
*   **File:** `src/orchestrator/content_orchestrator.py`
    *   **Function:** `orchestrate_content_generation(batch_size: int, variations_per_combo: int) -> GenerationResults`
    *   **Logic:** Query pending specs → Retrieve schemas → Generate multiple variations per combo → Validate → Store
    *   **Features:** Variation seeding for diverse exercises, batch processing, progress tracking

*   **File:** `src/services/llm/schema_aware_generator.py`
    *   **Function:** `generate_with_schema(spec: GenerationSpec, schema: ExerciseSchema) -> dict`
    *   **Logic:** LLM generation with schema-specific prompts and output validation

#### 3.3.4 Content Validation & Quality Assurance
*   **File:** `src/services/validation/content_validator.py`
    *   **Function:** `validate_exercise_content(exercise: Exercise, schema: ExerciseSchema) -> ValidationResult`
    *   **Logic:** Multi-level validation (schema compliance, content quality, language appropriateness)

#### 3.3.5 Pipeline Management & Execution
*   **File:** `src/orchestrator/pipeline_manager.py`
    *   **Function:** `run_full_pipeline(language_pairs: List[str], levels: List[str]) -> PipelineStatus`
    *   **Logic:** Executes complete curriculum generation pipeline with progress tracking

*   **File:** `scripts/run_curriculum_generation.py`
    *   **Function:** `main()` - Entry point for curriculum generation pipeline
    *   **Usage:** `python scripts/run_curriculum_generation.py --batch-size 5 --variations 10`

### 3.4 Business & Monetization
Enforces the "freemium" rules.

*   **File:** `src/services/business/limits.py`
    *   **Function:** `check_allowance(user_id) -> bool`
        *   *Logic:* Checks Redis counter `daily_msgs_{user_id}`. If > 20 and `is_premium=False`, returns False.
    *   **Function:** `consume_allowance(user_id)`
        *   *Logic:* Increments Redis counter.
*   **File:** `src/services/business/monetization.py`
    *   **Function:** `generate_checkout_link(user_id)`
        *   *Logic:* Calls Stripe API to create a session. Embeds `user_id` in metadata.
    *   **Function:** `handle_subscription_success(payload)`
        *   *Logic:* Webhook handler. Updates DB `users.is_premium = True`.

### 3.4 Growth & Experiments
Data-driven optimization engine.

*   **File:** `src/services/growth/ab_testing.py`
    *   **Function:** `get_variant(user_id, experiment_name)`
        *   *Logic:* Deterministic hash (e.g., `hash(id) % 2`) to assign users to "Funny Tone" vs "Strict Tone" groups.
*   **File:** `src/services/growth/clustering.py`
    *   **Function:** `analyze_user_behavior(days=30)`
        *   *Logic:* Async job. Clusters users based on error patterns (e.g., "Struggles with Verbs") to recommend specific modules.

### 3.5 Data Access Layer
*   **File:** `src/data/repositories/user_repo.py`
    *   *Functions:* `get_user_by_whatsapp`, `update_streak`, `save_quiz_result`.
*   **File:** `src/data/repositories/content_repo.py`
    *   *Functions:* `fetch_random_exercise(level, topic, exclude_ids=[])`.

---

## 4. Progressive Development Plan (High-Level Phases)

### Phase I: Minimal Skeleton (WhatsApp + LLM Connectivity)
*   Setup basic Orchestrator (Event Loop).
*   Connect WhatsApp Webhook via Twilio API (Receive -> Log -> Echo).
*   Connect LLM Gateway (Sync mode only).
*   **Outcome:** A bot that replies to "Hello" using GPT-4o-mini.

### Phase II: The Self-Learning Brain (Logic & Evals)
*   Implement `router.py` for command handling.
*   Implement `judge_correctness.py` (The feedback loop).
*   Setup LangSmith tracing for all interactions.
*   **Outcome:** A bot that can grade a single sentence and give feedback.

### Phase III: Business & Persistence (The Product)
*   Implement `session_manager.py` (DB persistence).
*   Implement `monetization.py` (Stripe & Limits).
*   Implement `scheduler.py` (Daily reset of limits).
*   **Outcome:** A sellable product with limits and memory.

### Phase IV: Growth & Async Scale
*   Implement `content_agent.py` (Generate 1000s of exercises).
*   Implement `ab_testing.py`.
*   Implement basic Voice/Audio support using ElevenLabs.
*   Setup Celery for async background tasks.
*   **Outcome:** A scalable, data-driven platform ready for 10k+ users.

### Phase V: Hyper-Personalization
*   Implement `clustering.py` for user segmentation.
*   Advanced Voice/Audio support in `whatsapp/io.py` using ElevenLabs.
*   Prepare migration path from Twilio to WhatsApp Business API.