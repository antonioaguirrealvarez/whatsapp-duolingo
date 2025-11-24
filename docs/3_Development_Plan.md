I will rewrite **Phase I** of the **Development Plan** (`docs/3_Development_Plan.md`) to be comprehensive, granular, and sequentially correct, incorporating all the missing activities you identified (typing indicators, tool usage, orchestration logic, E2E testing).

### Recommended Action
Please replace the content of **Phase I** in `docs/3_Development_Plan.md` with the following detailed breakdown. (I will keep Phase II as it was for now, or you can choose to expand it later).

```markdown:docs/3_Development_Plan.md
# 📅 DETAILED DEVELOPMENT PLAN
**Focus:** Phase I (Skeleton) & Phase II (Brain)
**Strategy:** Atomic execution with Test-Driven Development (TDD).

---

## 🔴 PHASE I: MINIMAL WHATSAPP + LLM MVP (The Skeleton)
**Goal:** A deployed bot that can receive a message, process it via a basic LLM (with tools), and reply with Text/Buttons/Lists.
**Definition of Done:** User says "Hola" -> Bot shows typing -> Bot replies "Hola! Ready?" -> User sees a Menu.

### Sub-Phase 1.1: Infrastructure & WhatsApp Connectivity (The Pipes)
*Goal: Establish bidirectional communication with WhatsApp Graph API.*

#### Activity 1.1.1: Project Skeleton & Environment
*   **Files:** `pyproject.toml`, `.env.example`, `src/core/config.py`.
*   **Functions:** `get_settings()`.
*   **Action:** Initialize Poetry. Define `WHATSAPP_TOKEN`, `VERIFY_TOKEN`, `OPENAI_API_KEY`, `FIRECRAWL_API_KEY`. Setup `pydantic-settings`.
*   **Test:** `pytest tests/core/test_config.py` (Verify env loading and type checking).

#### Activity 1.1.2: Webhook Verification (The Handshake)
*   **Files:** `src/api/routes/webhook_whatsapp.py`.
*   **Functions:** `verify_webhook(request: Request)`.
*   **Action:** Implement `GET /webhook`. Check `hub.mode` and `hub.verify_token`. Return `hub.challenge`.
*   **Implementation:** Use Twilio API for WhatsApp connectivity with scaffoldings for future migration to WhatsApp Business API.
*   **Pitfall:** Returning 403 or failing to return the challenge integer causes WhatsApp to reject the URL.

#### Activity 1.1.3: Ingress & Logging (The Ear)
*   **Files:** `src/api/routes/webhook_whatsapp.py`, `src/services/whatsapp/utils.py`.
*   **Functions:** `receive_message(payload: Dict)`, `extract_message_data(payload)`.
*   **Action:** Implement `POST /webhook`.
    1.  Verify `X-Hub-Signature-256` (Security).
    2.  Log raw JSON.
    3.  Return `200 OK` immediately (Asynchronous processing pattern).
*   **Test:** Use Postman to send a mock WhatsApp JSON payload. Verify logs.

#### Activity 1.1.4: Outbound Text & Typing Indicators (The Mouth)
*   **Files:** `src/services/whatsapp/client.py`.
*   **Functions:**
    *   `send_message(to: str, body: str)`
    *   `mark_as_read(message_id: str)`
    *   `set_typing_state(to: str, state: str = 'typing')` - *Crucial for UX*.
*   **Action:** Specific HTTP requests to `https://graph.facebook.com/v18.0/{phone_id}/messages`.
*   **Test:** `tests/integration/test_whatsapp_send.py` (Send "Hello World" and Typing indicator to developer number).

#### Activity 1.1.5: Rich UI Elements (Buttons & Lists)
*   **Files:** `src/services/whatsapp/templates.py`, `src/services/whatsapp/client.py`.
*   **Functions:**
    *   `send_interactive_buttons(to: str, text: str, buttons: List[str])`
    *   `send_interactive_list(to: str, header: str, rows: List[Dict])` (The "Droplist/Modal").
    *   `handle_emoji(text: str)` (Ensure encoding works).
*   **Action:** Construct the complex JSON for "Reply Buttons" (max 3) and "List Messages" (up to 10 rows).
*   **Test:** Send a "Choose Difficulty" menu. Verify it renders on mobile.

#### Activity 1.1.6: Metadata Extraction (Who is this?)
*   **Files:** `src/services/whatsapp/utils.py`.
*   **Functions:**
    *   `extract_user_profile(payload: Dict) -> Dict`: Returns `{'name': 'Juan', 'wa_id': '521...', 'phone': '...'}`.
    *   `extract_media_info(payload: Dict) -> Optional[Dict]`: Captures Image/Audio IDs if sent.
*   **Action:** Parse the nested JSON to get the user's display name (push name) to address them personally.
*   **Test:** Mock a payload with a profile name "Juan" and assert extraction works.


---

### Sub-Phase 1.2: LLM Gateway & Tools (The Brain)
*Goal: A flexible reasoning engine that can use tools.*

#### Activity 1.2.1: LangChain Foundation (Sync)
*   **Files:** `src/services/llm/gateway.py`.
*   **Functions:** `init_model(temperature: float)`, `get_response(user_text: str)`.
*   **Action:** Setup `ChatOpenAI` with `gpt-4o-mini` using LangChain v1.
*   **Test:** `tests/unit/test_llm_gateway.py` (Mock OpenAI API, assert valid string response).

#### Activity 1.2.2: Prompt Manager & Templates
*   **Files:** `src/services/llm/prompts/manager.py`, `src/services/llm/prompts/templates/tutor.jinja2`.
*   **Functions:** `render_prompt(template_name: str, context: Dict)`.
*   **Action:** Decouple prompts from code. Use Jinja2 for dynamic variable injection (User Name, Level).
*   **Content:** Create the "Viral Persona" system prompt (Sarcastic but helpful).

#### Activity 1.2.3: Tool Integration (Web Search)
*   **Files:** `src/services/llm/tools/web_search.py`.
*   **Functions:** `search_web(query: str)`.
*   **Action:** Implement a simple tool using `Firecrawl` API.
*   **Integration:** Bind this tool to the LangChain model using `.bind_tools()`.
*   **Test:** Ask LLM "What is the slang for 'cool' in Mexico City 2024?" and verify it calls the tool.

---

### Sub-Phase 1.3: The Orchestrator (The Coordinator)
*Goal: Tie The Ear, The Mouth, and The Brain together.*

#### Activity 1.3.1: The Event Loop & Router
*   **Files:** `src/orchestrator/core.py`, `src/orchestrator/router.py`.
*   **Functions:** `process_event(event: WhatsAppEvent)`.
*   **Action:**
    1.  Receive Event.
    2.  `client.mark_as_read()`.
    3.  `client.set_typing_state('typing')`.
    4.  `router.route(event)` -> Decide if it's a Command or Chat.

#### Activity 1.3.2: Session Management (In-Memory MVP)
*   **Files:** `src/orchestrator/session.py`.
*   **Functions:** `get_history(user_id)`, `update_history(user_id, msg)`.
*   **Action:** Simple Dict store to keep conversation context window (last 5 messages) so the LLM knows what's happening.

#### Activity 1.3.3: The Coordination Flow
*   **Files:** `src/orchestrator/flows/chat.py`.
*   **Functions:** `run_chat_flow(user_id, message)`.
*   **Logic:**
    *   Retrieve History.
    *   Call LLM Gateway (with Tools).
    *   Receive Text Response.
    *   Call `whatsapp.send_message`.
    *   (Optional) If LLM suggests a drill, Call `whatsapp.send_interactive_buttons`.

---

### Sub-Phase 1.4: Quality Assurance
*Goal: Ensure the system works end-to-end.*

#### Activity 1.4.1: E2E Integration Suite
*   **Files:** `tests/e2e/test_full_flow.py`.
*   **Action:** Simulate a full user lifecycle script.
    *   User: "Hola"
    *   System: (Verifies `set_typing` called) -> (Verifies LLM called) -> (Verifies `send_message` called).
*   **Tool:** Use `pytest-asyncio` and `respx` to mock external HTTP calls (WhatsApp & OpenAI) but test the internal wiring logic.


## 🟠 PHASE II: SELF-LEARNING (The Brain)
**Goal:** The system understands *quality*. It grades the user, tracks progress, and improves itself.
**Definition of Done:** User answers incorrectly -> Bot explains *why* -> Bot remembers the error -> Content is auto-generated for multiple languages.

### Sub-Phase 2.1: The "Judge" (Evaluations)
*Automated grading of user input using LLM-as-a-Judge.*

#### Activity 2.1.1: Correctness Evaluator Chain
*   **Files:** `src/services/llm/evals/judge_correctness.py`.
*   **Functions:** `evaluate_response(question: str, user_answer: str, rubric: str)`.
*   **Action:** Implement a structured LangChain chain that outputs JSON:
    ```json
    { "is_correct": false, "error_type": "grammar", "feedback_key": "verb_conjugation" }
    ```
*   **Test:** `tests/unit/test_judge.py`. Feed 10 hardcoded (Question, Wrong Answer) pairs. Assert `is_correct` is False.

#### Activity 2.1.2: Tone & Style Evaluator
*   **Files:** `src/services/llm/evals/judge_tone.py`.
*   **Functions:** `assess_virality(bot_response: str)`.
*   **Action:** Ensure the bot isn't being boring. If score < 7/10, regenerate response with higher "sassiness".
*   **Test:** `tests/unit/test_tone.py`. Feed a boring string "The answer is blue." Assert score < 5. Feed a fun string. Assert score > 8.

#### Activity 2.1.3: Observability (LangSmith)
*   **Files:** `src/core/config.py`, `src/services/llm/langsmith_client.py`.
*   **Action:** Enable `LANGCHAIN_TRACING_V2`. Create a Project "Whatsapp-Tutor-Prod".
*   **Goal:** Log every user interaction, token usage, and latency.
*   **Test:** Run the E2E script from Phase I. Verify a trace appears in the LangSmith web UI.

---

### Sub-Phase 2.2: Persistence & Storage Layer (The Memory)
*Setting up the brain's long-term memory before generating content.*

#### Activity 2.2.1: Database Schema & Models
*   **Files:** `src/data/models.py`.
*   **Action:** Define SQLAlchemy models:
    *   `User` (wa_id, name, level, native_lang, target_lang).
    *   `Topic` (e.g., "Travel", "Flirting").
    *   `Exercise` (Question, Answer, Difficulty, Language Pair, Type).
    *   `Lesson` (Collection of 10 exercises).
    *   `UserProgress` (user_id, exercise_id, is_correct, timestamp).
*   **Test:** `tests/integration/test_db_schema.py`. Create one of each object and commit to a test DB.

#### Activity 2.2.2: Migration System
*   **Files:** `alembic.ini`, `src/data/migrations/`.
*   **Action:** Initialize Alembic. Create initial migration script. Apply to local PostgreSQL.
*   **Test:** Run `alembic upgrade head` on a fresh DB container.

#### Activity 2.2.3: Repository Pattern Implementation
*   **Files:** `src/data/repositories/user_repo.py`, `src/data/repositories/content_repo.py`.
*   **Functions:**
    *   `get_or_create_user(wa_id)`.
    *   `save_exercise_result(user_id, result)`.
    *   `fetch_lesson_batch(level, topic, count)`.
*   **Action:** Abstract raw SQL queries. Ensure all DB access goes through these repos.
*   **Test:** `tests/integration/test_repos.py`. Insert user -> Fetch user -> Assert equality.

---

### Sub-Phase 2.3: Advanced Content Factory (Schema-Driven Curriculum Generation)
*Multi-layered content generation with curriculum parsing, schema mapping, and structured output validation.*

#### Activity 2.3.1: Curriculum Structure Parser & Database
*   **Files:** `src/services/curriculum/parser.py`, `src/services/curriculum/curriculum_database.py`, `scripts/init_curriculum_database.py`.
*   **Functions:** 
    *   `parse_curriculum_from_database() -> List[CurriculumCombination]`
    *   `extract_generation_specs(combinations) -> List[GenerationSpec]`
    *   `get_pending_combinations(limit) -> List[GenerationSpec]`
    *   `update_generation_status(combo_id, status, count) -> bool`
*   **Action:**
    1.  Create standardized ID system (LANG_001, CAT_VOCAB, EX_MCQ, TOPIC_DAILY, COMBO_001)
    2.  Initialize curriculum database with 54 MVP combinations (2 language pairs × 1 level × 3 categories × 3 types × 3 topics)
    3.  Build parser to extract combinations and convert to generation specifications
    4.  Implement status tracking (pending → in_progress → completed/failed)
    5.  Add filtering capabilities by language, level, category, exercise type, topic
*   **Database Schema:** `curriculum.db` with tables for language_pairs, cefr_levels, content_categories, exercise_types, topics, curriculum_structure
*   **Test:** `tests/unit/test_curriculum_parser.py`. Parse database, extract 54 specs, validate MVP matrix (27 Spanish→English + 27 Portuguese→English combinations).

#### Activity 2.3.2: Exercise Schema Registry
*   **Files:** `src/services/schema/exercise_schema.py`, `src/services/schema/registry.py`.
*   **Functions:** `get_schema_for_exercise_type(exercise_type: str) -> ExerciseSchema`, `validate_output_against_schema(output: dict, schema: ExerciseSchema) -> bool`.
*   **Action:**
    1.  Define input/output templates for each exercise type (Multiple Choice, Fill Blank, Roleplay, etc.)
    2.  Create JSON schemas for validation (required fields, field types, constraints)
    3.  Build schema registry database table mapping exercise types to their specifications
    4.  Include field-level validation rules and example templates
*   **Test:** `tests/unit/test_exercise_schema.py`. Validate Fill-in-blank schema requires specific fields.

#### Activity 2.3.3: Schema-Aware Content Generation Orchestrator
*   **Files:** `src/orchestrator/content_orchestrator.py`, `src/services/llm/schema_aware_generator.py`.
*   **Functions:** `orchestrate_content_generation(batch_size: int)`, `generate_exercise_with_context(spec: GenerationSpec, schema: ExerciseSchema) -> Exercise`.
*   **Action:**
    1.  Query `curriculum_structure` table for pending exercise combinations
    2.  For each combination: retrieve schema from registry, build context-aware prompt
    3.  Generate content using LLM with schema-specific templates and validation
    4.  Validate output against schema before acceptance
    5.  Store validated exercises in main `exercises` table
    6.  Update generation status and metrics
*   **Test:** `tests/integration/test_content_orchestrator.py`. Generate B1 Grammar Fill-blank exercises, validate schema compliance.

#### Activity 2.3.4: Content Validation & Quality Assurance
*   **Files:** `src/services/validation/content_validator.py`, `src/services/validation/quality_metrics.py`.
*   **Functions:** `validate_exercise_content(exercise: Exercise, schema: ExerciseSchema) -> ValidationResult`, `calculate_quality_score(exercise: Exercise) -> float`.
*   **Action:**
    1.  Implement multi-level validation (schema compliance, content quality, language appropriateness)
    2.  Add duplicate detection and content similarity checks
    3.  Create quality scoring system based on multiple criteria
    4.  Implement retry mechanisms for failed generations
    5.  Log all validation results for quality monitoring
*   **Test:** `tests/unit/test_content_validation.py`. Test validation passes good content, rejects bad content.

#### Activity 2.3.5: Multi-Language Curriculum Generation Pipeline
*   **Files:** `scripts/run_curriculum_generation.py`, `src/orchestrator/pipeline_manager.py`.
*   **Functions:** `run_full_pipeline(language_pairs: List[str], levels: List[str])`, `monitor_generation_progress() -> PipelineStatus`.
*   **Action:**
    1.  Execute full pipeline: Parse curriculum → Load schemas → Generate content → Validate → Store
    2.  Support concurrent generation with rate limiting and error handling
    3.  Implement progress tracking and resumable generation
    4.  Generate comprehensive reports on content coverage and quality metrics
    5.  Support incremental updates and delta generation
*   **Goal:** Generate complete curriculum matrix for MVP (B1 × 4 categories × 4 types × 9 topics = 144 combinations)
*   **Test:** `tests/e2e/test_curriculum_pipeline.py`. Run full pipeline, verify all combinations generated successfully.

---

### Sub-Phase 2.4: Structured Onboarding
*Assessing the user and remembering them.*

#### Activity 2.4.1: Adaptive Placement Test Logic
*   **Files:** `src/orchestrator/flows/onboarding.py`.
*   **Action:** Implement a Decision Tree:
    *   Step 1: Ask "Native Language?" (List: Español, Português).
    *   Step 2: Send A1 Question (in target lang).
    *   Step 3: If Correct -> Send B1 Question. If Wrong -> Set Level = A1.
    *   Step 4: Save `level` and `native_lang` to DB via `user_repo`.
*   **UI:** Use WhatsApp "List Message" for multiple-choice answers to reduce friction.
*   **Test:** `tests/unit/test_onboarding_logic.py`. Mock user answers sequence (Correct, Correct, Wrong) -> Assert Level = B1.

#### Activity 2.4.2: Onboarding Flow UI Tests
*   **Files:** `tests/integration/test_onboarding_flow.py`.
*   **Action:** Simulate the state machine.
    *   User sends "Hola".
    *   Bot sends Language List.
    *   User selects "Español".
    *   Bot sends Question 1.
*   **Assertion:** Verify DB state updates correctly at each step.

---

### Sub-Phase 2.5: Quality Assurance & E2E Testing (The Final Exam)
*Goal: Verify the entire "Self-Learning" loop works before release.*

#### Activity 2.5.1: The "Perfect Student" Simulation
*   **Files:** `tests/e2e/test_learning_loop.py`.
*   **Action:** Script a full user journey:
    1.  **Onboarding:** User joins -> Takes Test -> Gets placed in A2.
    2.  **Lesson:** User requests lesson -> Bot serves "Ordering Food" (A2).
    3.  **Mistake:** User answers wrong ("I want taco").
    4.  **Correction:** Bot explains error ("I *would like* a taco").
    5.  **Memory:** Check `UserProgress` table to ensure mistake was logged.
*   **Tool:** `pytest` + `respx` (mocking OpenAI/WhatsApp to save costs) AND a separate "Live" run against real APIs.

#### Activity 2.5.2: Load Testing the Content Factory
*   **Files:** `tests/performance/test_content_generation.py`.
*   **Action:** Trigger generation of 100 exercises in parallel.
*   **Goal:** Ensure DB doesn't lock and Unique Constraints hold up under pressure.
*   **Metrics:** Average generation time per exercise < 2s.

#### Activity 2.5.3: Regression Suite
*   **Files:** `tests/regression/test_v1_parity.py`.
*   **Action:** Ensure Phase I features (basic chat, tools) didn't break with the new DB and Orchestrator changes.

## 🟢 PHASE III: MONETIZATION READY (The Business)
**Goal:** Turn users into paying customers & Scale content depth.
**Definition of Done:** User hits daily limit -> Paywall -> Pays via Stripe -> Limit lifted -> User accesses advanced C1 Roleplay content in French.

### Sub-Phase 3.1: The Landing Page (Frontend)
*A simple, high-converting page to handle payments.*

#### Activity 3.1.1: Next.js Project Setup
*   **Files:** `web/package.json`, `web/app/page.tsx`.
*   **Action:** Initialize Next.js 14 project with TailwindCSS.
*   **UI:**
    *   Hero Section: "Speak like a local, not a robot."
    *   Demo: GIF of WhatsApp chat.
    *   Pricing: "$9/mo" button.
*   **Test:** `npm run build` passes. Page loads on `localhost:3000`.

#### Activity 3.1.2: Stripe Checkout Integration
*   **Files:** `web/app/api/checkout/route.ts`, `web/lib/stripe.ts`.
*   **Action:**
    1.  Create API endpoint that accepts `?uid={wa_id}`.
    2.  Create Stripe Checkout Session (Mode: Subscription).
    3.  Add `wa_id` to Stripe Metadata (`client_reference_id`).
    4.  Redirect user to Stripe hosted page.
*   **Test:** Click button -> Redirect to Stripe -> Verify `wa_id` is in the URL params.

---

### Sub-Phase 3.2: Payment Logic & Webhooks (Backend)
*Connecting Stripe events to the User Database.*

#### Activity 3.2.1: Stripe Webhook Handler
*   **Files:** `src/api/routes/webhook_stripe.py`.
*   **Functions:** `handle_stripe_event(payload, sig_header)`.
*   **Action:**
    1.  Verify Stripe Signature (Security).
    2.  Listen for `checkout.session.completed`.
    3.  Extract `wa_id` from metadata.
    4.  Update DB: `User.is_premium = True`, `User.subscription_id = ...`.
*   **Test:** Use Stripe CLI to trigger a mock event `stripe trigger checkout.session.completed`. Assert DB updates.

#### Activity 3.2.2: Subscription Management
*   **Files:** `src/services/business/monetization.py`.
*   **Functions:** `cancel_subscription(user_id)`, `handle_payment_failed(user_id)`.
*   **Action:** Handle `invoice.payment_failed` -> Downgrade user to Free.
*   **Test:** Trigger payment failure event -> Assert `User.is_premium` becomes False.

---

### Sub-Phase 3.3: Daily Limits Engine
*Enforcing scarcity to drive upgrades.*

#### Activity 3.3.1: Usage Tracking
*   **Files:** `src/services/business/limits.py`, `src/orchestrator/core.py`.
*   **Action:**
    *   Add `daily_lessons_count` column to `User` table.
    *   On every lesson completion, increment count.
    *   Reset count at 00:00 UTC via Cron (or lazily on first access of the day).

#### Activity 3.3.2: The Paywall Logic
*   **Files:** `src/orchestrator/router.py`.
*   **Logic:**
    *   Before starting a lesson:
        ```python
        if user.daily_lessons_count >= 1 and not user.is_premium:
            return send_paywall_message(user)
        ```
    *   **Paywall Message:** "You're on fire! 🔥 Unlock unlimited lessons for $9/mo." + [Link to Web with ?uid=].
*   **Test:** `tests/integration/test_limits.py`. Set count to 1. Mock Free User. Assert Paywall Triggered. Mock Paid User. Assert Lesson Starts.

---

### Sub-Phase 3.4: Advanced Retention (Streaks & Stats)
*Gamification to keep users coming back.*

#### Activity 3.4.1: Streak System
*   **Files:** `src/services/business/analytics.py`.
*   **Action:**
    *   Logic: If `last_lesson_date` == yesterday, `streak += 1`. If older, `streak = 1`.
    *   Display: "🔥 5 Day Streak!" in daily greeting.
*   **Test:** Manipulate timestamps in DB. Verify streak calculation logic.

#### Activity 3.4.2: "My Progress" Command
*   **Files:** `src/orchestrator/flows/stats.py`.
*   **Action:** Handle "menu" or "profile" command.
*   **Output:** Generate an image (using Pillow or just text) showing:
    *   Level: B1
    *   Streak: 12 Days
    *   Plan: Free (Upgrade?)

---

### Sub-Phase 3.5: Content Scale & Expansion (More Brain Power)
*Adding depth to the curriculum and intelligence.*

#### Activity 3.5.1: Specialized Judges (The Critics)
*   **Files:** `src/services/llm/evals/`.
*   **Action:** Implement 3 new strict judges:
    1.  `judge_spelling.py`: Rejects typos (e.g., "thier" vs "their"). Strictness: High.
    2.  `judge_grammar_detailed.py`: Explains subtle errors (e.g., "I will go" vs "I am going").
    3.  `intent_classifier.py` (The Meta Judge): Detects if user is saying "Wait, go back", "Explain that again", "Billing issue".
*   **Test:** Unit tests with edge cases ("I want 2 go" -> Spelling Error).

#### Activity 3.5.2: Advanced Lesson Types (C1/C2)
*   **Files:** `src/services/llm/agents/content_agent.py`.
*   **Action:** Generate complex scenarios for Paid users:
    *   **Roleplay:** "You are negotiating a salary raise. The boss is tough."
    *   **Audio:** "Listen to this voice note (TTS) and transcribe it."
    *   **Debate:** "Argue *for* remote work."
*   **Test:** Generate 10 Roleplay scenarios. verify prompt complexity.

#### Activity 3.5.3: New Language Expansion (French)
*   **Files:** `scripts/seed_curriculum.py`.
*   **Action:** Run Content Factory for **English → French**.
    *   Topics: "Bakery", "Metro", "Fashion".
    *   Curriculum: 500 exercises (A1-B2).
*   **UI:** Update Onboarding list to include "Français" as a target option.


### Sub-Phase 3.6: Quality Assurance & E2E Testing (Monetization)
*Goal: Ensure money flows correctly and limits work perfectly.*

#### Activity 3.6.1: The "Freeloader" Simulation
*   **Files:** `tests/e2e/test_paywall.py`.
*   **Action:** Script a user journey:
    1.  User completes Lesson 1 (Free).
    2.  User attempts Lesson 2 immediately.
    3.  **Assert:** Bot sends Paywall Message (Not a lesson).
    4.  **Assert:** Bot does *not* call LLM for new content.

#### Activity 3.6.2: The "VIP" Upgrade Simulation
*   **Files:** `tests/e2e/test_upgrade_flow.py`.
*   **Action:**
    1.  Mock Stripe Webhook call (`checkout.session.completed`) for `wa_id=123`.
    2.  **Assert:** DB `is_premium` becomes True.
    3.  User `123` requests Lesson 2.
    4.  **Assert:** Bot serves Lesson 2 (Paywall lifted).

#### Activity 3.6.3: Content & Judge Regression
*   **Files:** `tests/regression/test_advanced_content.py`.
*   **Action:**
    1.  Test the new "Spelling Judge" with "Hullo" -> Expect rejection.
    2.  Test the new "Meta Judge" with "Wait stop" -> Expect flow interruption (not graded as an answer).

## 🟢 PHASE IV: MULTIMODAL & GROWTH (The Expansion)
**Goal:** Engaging senses (Voice), expanding reach (Languages), and optimizing growth.
**Definition of Done:** User sends Audio -> Bot replies with Audio -> User gets Weekly Progress Report -> User refers a friend.

### Sub-Phase 4.1: Multimodal Capabilities (Voice)
*Speaking and Listening features.*

#### Activity 4.1.1: Audio Ingress (STT)
*   **Files:** `src/services/whatsapp/io.py`, `src/services/ai/voice.py`.
*   **Functions:** `transcribe_audio(media_id)`.
*   **Action:**
    1.  Download OGG file from WhatsApp URL.
    2.  Send to ElevenLabs STT API (or OpenAI Whisper for fallback).
    3.  Return text to Orchestrator.
*   **Test:** `tests/integration/test_voice.py`. Send sample .ogg. Assert correct text transcription.

#### Activity 4.1.2: Audio Egress (TTS)
*   **Files:** `src/services/ai/voice.py`.
*   **Functions:** `generate_speech(text, voice_id)`.
*   **Action:** Use ElevenLabs TTS to generate audio. Upload to S3/Cloudinary. Get URL. Send to WhatsApp.
*   **Test:** Generate "Hello". Specific check for file size > 0 and valid URL.

#### Activity 4.1.3: Voice Interaction Flow
*   **Files:** `src/orchestrator/flows/voice_chat.py`.
*   **Action:** Update Router. If `msg_type == audio`:
    *   Transcribe -> LLM -> TTS -> Reply with Audio + Text Transcript.
*   **Test:** Mock Input Audio. Verify Output contains both Audio Attachment and Text Body.

---

### Sub-Phase 4.2: Content Expansion & Localization
*More languages and deeper personalization.*

#### Activity 4.2.1: New Languages (Italian, German)
*   **Files:** `scripts/seed_curriculum.py`.
*   **Action:** Run Content Agent for:
    *   English -> Italian (Topics: Food, Art, Gestures).
    *   English -> German (Topics: Engineering, Travel, Bureaucracy).
*   **Test:** Verify DB has > 200 exercises for `target_lang='it'` and `target_lang='de'`.

#### Activity 4.2.2: Country-Specific Localization
*   **Files:** `src/services/llm/prompts/manager.py`.
*   **Action:** Inject `user_country` into System Prompt.
    *   If **Mexico** -> Use "Chido", "Güey".
    *   If **Argentina** -> Use "Che", "Boludo".
    *   If **Spain** -> Use "Vale", "Tío".
*   **Test:** `tests/unit/test_localization.py`. Simulate User from MX. Ask "How are you?". Expect Mexican slang in response.

#### Activity 4.2.3: Advanced Exercise Types
*   **Files:** `src/services/llm/agents/content_agent.py`.
*   **Action:** Add new generators for:
    *   **Pronunciation:** "Read this sentence aloud." (Evaluated via STT confidence).
    *   **Listening:** "Listen to this clip and answer."
*   **Test:** Generate 10 Listening exercises. Verify they have associated audio_url fields.

---

### Sub-Phase 4.3: Deep Analytics & Progress Tracking
*Measuring learning velocity.*

#### Activity 4.3.1: Knowledge Graph Implementation
*   **Files:** `src/services/analytics/mastery.py`.
*   **Action:** Track correctness per *tag* (e.g., "Past Tense": 80%, "Subjunctive": 20%).
*   **Logic:** Update score after every exercise in `UserProgress` table.
*   **Test:** Simulate 5 correct Past Tense answers. Assert "Past Tense" mastery > 0.8.

#### Activity 4.3.2: Weekly Progress Report
*   **Files:** `src/orchestrator/scheduler.py`, `src/services/whatsapp/templates.py`.
*   **Action:** Cron job (Sunday 9am). Generate visual summary:
    *   "You learned 50 words this week!"
    *   "Top strength: Travel Vocabulary."
    *   "Focus area: Verbs."
*   **Test:** Force run cron job. Verify message generation logic.

---

### Sub-Phase 4.4: Growth Engine
*Viral loops and experiments.*

#### Activity 4.4.1: A/B Testing Framework
*   **Files:** `src/services/growth/ab_testing.py`.
*   **Action:** Split users into buckets (Variant A: Strict Tutor, Variant B: Funny Tutor).
*   **Test:** Create 100 users. Assert ~50/50 split.

#### Activity 4.4.2: Referral System
*   **Files:** `src/orchestrator/flows/referral.py`.
*   **Action:** "Invite a friend = 1 Week Pro Free".
    *   Generate unique referral link `wa.me/...?text=ref_123`.
    *   Track conversions.
*   **Test:** Simulate User B joining via User A's link. Verify User A gets reward.

---

### Sub-Phase 4.5: Quality Assurance & E2E Testing (Multimodal)
*Goal: Verify Voice, Growth, and Analytics.*

#### Activity 4.5.1: Voice Conversation E2E
*   **Files:** `tests/e2e/test_voice_flow.py`.
*   **Action:**
    1.  Upload OGG "Hello".
    2.  Assert Bot transcribes correctly.
    3.  Assert Bot replies with Audio message.
    4.  Assert Bot reply text matches Audio content.

#### Activity 4.5.2: Analytics Accuracy Test
*   **Files:** `tests/data/test_analytics_integrity.py`.
*   **Action:** Replay a sequence of 50 events. Recalculate Mastery scores. Compare with live DB scores.

#### Activity 4.5.3: Localization Regression
*   **Files:** `tests/regression/test_locale.py`.
*   **Action:** Ensure Mexican slang doesn't leak into Argentinian users' sessions.
