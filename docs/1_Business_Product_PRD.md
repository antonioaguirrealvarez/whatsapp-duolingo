# 🎯 PRODUCT REQUIREMENTS DOCUMENT (PRD)
**Product:** WhatsApp-First AI Language Tutor for LATAM
**Positioning:** "Duolingo inside WhatsApp — but faster, funnier, more human, and designed for the TikTok generation."

---

## 1. Product Vision
### 1.1 High-Level Vision
Build the most convenient, culturally fluent, and addictive AI language-learning assistant for LATAM adults (Gen Z & Millennials). Delivered entirely inside WhatsApp, it combines micro-learning with a "viral personality"—a mix of teacher, friend, and comedian.
### 1.2 Core Philosophy
*   **Frictionless:** No new app to install. It lives where users already spend 8 hours a day.
*   **Personality-First:** The AI isn't a robot; it's a character that roasts you, encourages you, and uses local slang.
*   **Viral by Design:** Content is optimized for screenshots and social sharing.

---

## 2. Target User
### 2.1 Primary Persona: "The Aspiring Zoomer/Millennial"
*   **Demographics:** Age 18–35, LATAM (Mexico, Brazil, Colombia, Argentina).
*   **Behavior:** Heavy WhatsApp/Instagram/TikTok user. "Doom scroller."
*   **Motivation:** Wants better job opportunities (English/Portuguese) or travel skills but finds traditional apps boring or too slow.
*   **Pain Point:** Feels guilty about not studying but lacks time for 30-min sessions. Needs immediate gratification.

### 2.2 User Motivations
*   **Social Currency:** Wants to share funny interactions (screenshots).
*   **Career Growth:** Needs professional proficiency (CEFR A1 -> C2).
*   **Convenience:** Wants to learn while commuting or waiting in line.

---

## 3. Product Objectives
### 3.1 Functional Objectives
*   **Platform:** Operate 100% within WhatsApp (using Lists, Buttons, and Modals where possible).
*   **Curriculum:** Structured A1–C2 progression (Vocab, Grammar, Conversation).
*   **Assessment:** Reliable placement tests and continuous evaluation via LLM Judges.
*   **Daily Limits:** Enforce **1 lesson per day** for free users; unlimited for paid.
*   **Tech Stack:** Leverage LangChain v1 for orchestration and LangSmith for evaluations.

### 3.2 Business Objectives
*   **Monetization:** Convert free users to paid subscriptions via Stripe (linked to WhatsApp ID).
*   **Retention:** High daily active use through streak mechanics and push notifications (within 24h window).
*   **Growth:** Organic growth via "Share this roast" mechanics.

---

## 4. User Experience & Interaction Model
### 4.1 Onboarding Flow (Structured)
1.  **Welcome:** Friendly, slightly witty greeting.
2.  **Placement Test (Crucial):**
    *   Instead of self-reporting, the user takes a rapid adaptive quiz.
    *   Result maps to **CEFR Levels (A1, A2, B1, B2, C1, C2)**.
    *   *Example:* "You are B1 (Intermediate). You can handle travel but need work on professional emails."
3.  **Goal Setting:** "Just for fun" vs. "Professional".
4.  **First Lesson:** Immediate delivery of content matching the determined level.

### 4.2 The Core Learning Loop
1.  **Trigger:** User starts session or responds to a notification.
2.  **Context Retrieval:** System pulls user level, history, and personality preferences.
3.  **Content Generation (Live):**
    *   Exercise generated dynamically (or pulled from pre-generated pool).
    *   **Format:** Multiple choice (WhatsApp Buttons), Fill-in-the-blank, Voice note response.
4.  **User Response:** User replies via text or voice.
5.  **LLM Evaluation (The Judge):**
    *   Checks correctness, grammar, and *tone*.
    *   **Feedback:** "Correct! But you sound like a textbook. Locals say it like this..."
6.  **Progression:** Update progress bar (e.g., "Grammar Unit 3: 40% complete").

### 4.3 Daily Limits (Monetization)
*   **Free User:**
    *   1 Full Lesson / Day.
    *   After completion: "You're on fire! 🔥 Want to keep going? Upgrade to Pro or wait for tomorrow."
*   **Pro User:** Unlimited lessons, voice mode access, specialized roleplay scenarios.

---

## 5. Functional Architecture (High-Level)
*Per technical requirements, the system is modularized for scalability.*

### 5.1 Connectivity Layer
*   **WhatsApp Webhook:** Dumb pipe. Receives payload, verifies signature, passes to orchestrator.
*   **WhatsApp API:** Handles sending of Text, Media, Buttons, and Lists. Initially implemented via Twilio with scaffoldings for future migration to WhatsApp Business API.

### 5.2 The Brain (User Orchestrator)
*   **State Machine:** Tracks where the user is (Onboarding, Lesson, Payment Pending, Idle).
*   **Decision Engine:** "Does this user need a quiz? A reminder? Or a payment prompt?"
*   **Router:** Delegates tasks to the LLM Gateway or Database.

### 5.3 LLM Gateway & Infra (LangChain)
*   **Sync Content Generation:** Real-time responses for conversation practice.
*   **Async Content Generation:** Massive background generation of curriculum exercises (e.g., "Generate 500 B2 grammar questions using Mexican slang").
*   **Evals (LangSmith):**
    *   **Training Evals:** Check quality of async content before it goes live.
    *   **Live Evals:** "Judge" user answers for accuracy and grading.

### 5.4 Backend & Storage
*   **User DB:** Stores Profile, CEFR Level, Stripe Status, Streak Count.
*   **Content DB:** Stores generated lessons, history of user errors (for spaced repetition).

---

## 6. Content & Tone Strategy
### 6.1 The "Viral" Persona
*   **Tone:** Varies by user preference but defaults to "Witty Tutor."
*   **Style:** Uses emojis, local cultural references (e.g., mentioning local traffic, celebrities), and benevolent roasting.
*   **Safety:** High guardrails against hate speech, but allows for "spicy" humor.

### 6.2 Curriculum Structure
*   **Levels:** A1 to C2.
*   **Units:** 10 Units per Level.
*   **Modules:** Grammar, Vocabulary, Listening (Audio), Speaking (Voice), Roleplay (e.g., "Ordering Tacos").

---

## 7. Development Roadmap (Phases)

### Phase I: Minimal WhatsApp + LLM MVP ("The Skeleton")
*   **Goal:** Functional bot with basic plumbing.
*   **Features:**
    *   Env setup & Git structure.
    *   WhatsApp Webhook "Hello World".
    *   Basic Onboarding (Manual level selection for speed).
    *   Simple LLM Gateway connection (Sync generation).
    *   Single learning mode (Text-based conversation).

### Phase II: Self-Learning ("The Brain")
*   **Goal:** Intelligent assessment and structured curriculum.
*   **Features:**
    *   **CEFR Placement Test.**
    *   **LLM Judge integration (LangSmith)** for evaluating answers.
    *   **Async Content Engine:** Pre-generate robust curriculum.
    *   WhatsApp UI Polish: Use of Lists and Reply Buttons.

### Phase III: Monetization Ready ("The Business")
*   **Goal:** Payment infrastructure and limits.
*   **Features:**
    *   **Stripe Integration:** Checkout link generation with `?uid=`.
    *   **Daily Limits Engine:** 1 lesson/day logic.
    *   **User Memory:** Persistent state (Streaks, XP).
    *   **Landing Page V1:** SEO-optimized, sales focused.

### Phase IV: Multimodal ("The Senses")
*   **Goal:** Voice and high-engagement features.
*   **Features:**
    *   **STT/TTS (ElevenLabs):** High-quality AI audio for voice input/output.
    *   **Growth Engine:** A/B Testing framework for prompts/messages.

### Phase V: Hyper-Personalization
*   **Goal:** Predictive and deeply personal experience.
*   **Features:**
    *   **Persona Prediction:** Guess user city/job based on chat style.
    *   **Content Personalization:** "Here's a lesson on *Legal English* since you mentioned being a lawyer."

---

## 8. Monetization & Landing Page
### 8.1 Pricing Model
*   **Freemium:** 1 Lesson/Day.
*   **Premium:** Monthly subscription (Unlimited).

### 8.2 Landing Page Requirements
*   **Purpose:** Convert traffic to WhatsApp users & Convert free users to Paid.
*   **Key Sections:** Hero (Value Prop), Demo (Screenshots), Social Proof, Pricing, FAQ.
*   **Tech:** Simple, fast, SEO-optimized (e.g., Next.js or simple HTML/CSS).

---

## 9. Risks & Mitigations
1.  **WhatsApp Rate Limits:** Use queues and batching.
2.  **LLM Hallucinations:** Strict LangSmith evals and "Grounding" in generated curriculum.
3.  **Cost:** Cache common responses; use cheaper models for simple tasks (e.g., intent classification).