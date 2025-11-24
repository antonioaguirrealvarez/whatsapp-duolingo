# 🗄️ DATA SCHEMA & STORAGE PRD
**Project:** WhatsApp-First AI Language Tutor
**Version:** 1.0
**Status:** Draft
**Database Engine:** PostgreSQL 15+ (Production), Redis (Cache/Queues)

---

## 1. Entity Relationship Overview
The system revolves around the **User**.
*   **Users** have **Conversations** (Linear chat history).
*   **Users** have **Progress** linked to **Exercises**.
*   **Exercises** belong to **Topics** and are specific to a **Language Pair** (e.g., ES->EN).
*   **Users** have a **Subscription** state managed via Stripe.

---

## 2. Core Tables (User & Auth)

### 2.1 `users`
The central identity table.
*   `id`: **UUID** (Primary Key)
*   `whatsapp_id`: **VARCHAR(50)** (Unique, Indexed) - The phone ID from Meta API.
*   `display_name`: **VARCHAR(100)** - Extracted from WhatsApp Profile.
*   `phone_number`: **VARCHAR(20)** - Normalized E.164 format.
*   `created_at`: **TIMESTAMP WITH TIME ZONE** - Default `NOW()`.
*   `last_active_at`: **TIMESTAMP WITH TIME ZONE** - Updated on every message.
*   `timezone`: **VARCHAR(50)** - Inferred from country code or user setting.
*   `metadata`: **JSONB** - Stores inferred persona tags (e.g., `{"job": "lawyer", "city": "CDMX"}`).

### 2.2 `user_settings`
Preferences for the learning experience.
*   `user_id`: **UUID** (FK -> users.id)
*   `native_language`: **VARCHAR(2)** - (e.g., 'es', 'pt').
*   `target_language`: **VARCHAR(2)** - (e.g., 'en', 'fr').
*   `cefr_level`: **ENUM** ('A1', 'A2', 'B1', 'B2', 'C1', 'C2').
*   `daily_notification_time`: **TIME** - Default `09:00`.
*   `persona_style`: **ENUM** ('funny', 'strict', 'flirty') - Default 'funny'.

---

## 3. Curriculum & Content (The Content Factory)

### 3.1 `curriculum_topics`
Categorization of learning material.
*   `id`: **UUID** (PK)
*   `slug`: **VARCHAR(100)** (Unique) - e.g., `ordering-food`.
*   `name_en`: **VARCHAR(100)** - "Ordering Food".
*   `name_es`: **VARCHAR(100)** - "Pidiendo Comida".
*   `category`: **ENUM** ('travel', 'business', 'social', 'grammar').

### 3.2 `exercises`
The atomic unit of learning. Generated asynchronously by the Content Agent.
*   `id`: **UUID** (PK)
*   `topic_id`: **UUID** (FK -> curriculum_topics.id).
*   `source_lang`: **VARCHAR(2)** - Origin language (e.g., 'es').
*   `target_lang`: **VARCHAR(2)** - Learning language (e.g., 'en').
*   `difficulty_level`: **ENUM** ('A1', ... 'C2').
*   `exercise_type`: **ENUM** ('multiple_choice', 'fill_blank', 'roleplay', 'open_response', 'translation', 'error_identification').
*   `theory`: **TEXT** - Educational content explaining concepts, vocabulary, or grammar rules with examples.
*   `exercise_introduction`: **TEXT** - Instructions for the user explaining the exercise format and what they need to do.
*   `exercise_input`: **TEXT** - The actual exercise content (sentence with blanks, question with options, roleplay scenario).
*   `expected_output`: **TEXT** - The correct answer or expected response from the user.
*   `media_url`: **VARCHAR(255)** - URL for Audio/Image if applicable (S3 link).
*   `verification_hash`: **VARCHAR(64)** - To prevent duplicate generations.

### 3.3 Content Generation Field Specifications

#### Exercise Type Field Variations

#### 3.3.1 Fill-in-the-Blank Exercises
*   **exercise_introduction**: Instructions for filling blanks
    *   *Example:* "Fill in the blank with the correct word that best completes the sentence."
*   **exercise_input**: Sentence with missing word marked by underscores
    *   *Example:* "Mi hermana ___ muy inteligente." (underscore represents missing word)
*   **expected_output**: Single word or phrase that fills the blank
    *   *Example:* "es"

#### 3.3.2 Multiple Choice Exercises
*   **exercise_introduction**: Instructions for selecting from options
    *   *Example:* "Choose the correct option that best completes the sentence."
*   **exercise_input**: Sentence with blank followed by numbered options
    *   *Example:* "___ libro es interesante. [1] El [2] La [3] Los"
*   **expected_output**: Option number or the full correct phrase
    *   *Example:* "1" or "El libro es interesante."

#### 3.3.3 Roleplay Exercise
*   **exercise_introduction**: Scenario setup and role description
    *   *Example:* "You are at a restaurant in Madrid. Play the role of a customer ordering lunch. Respond to the waiter's question."
*   **exercise_input**: Scenario description with context
    *   *Example:* "Camarero: '¿Qué desea tomar?' (Waiter: 'What would you like to order?')"
*   **expected_output**: Appropriate response in target language
    *   *Example:* "Me gustaría una paella, por favor."

#### 3.3.4 Translation Exercises
*   **exercise_introduction**: Translation instructions
    *   *Example:* "Translate the following sentence from Spanish to English."
*   **exercise_input**: Source language sentence
    *   *Example:* "Ayer fui al mercado."
*   **expected_output**: Accurate translation in target language
    *   *Example:* "Yesterday I went to the market."

#### 3.3.5 Error Identification Exercises
*   **exercise_introduction**: Error-finding instructions
    *   *Example:* "Find and correct the error in the following sentence."
*   **exercise_input**: Sentence containing an error
    *   *Example:* "Yo estoy profesor." (incorrect - should use 'ser')
*   **expected_output**: Corrected sentence
    *   *Example:* "Yo soy profesor."

#### 3.3.6 Open Response Exercises
*   **exercise_introduction**: Open-ended response instructions
    *   *Example:* "Respond to the following question in a complete sentence."
*   **exercise_input**: Open-ended question
    *   *Example:* "¿Cómo te llamas y de dónde eres?"
*   **expected_output**: Complete personal response
    *   *Example:* "Me llamo Carlos y soy de México."

### Field Data Types and Constraints

#### `theory` Field
*   **Data Type:** TEXT
*   **Length:** 500-2000 characters
*   **Required:** Yes
*   **Format:** Plain text with educational content
*   **Validation:** Must contain educational value, not just filler

#### `exercise_introduction` Field
*   **Data Type:** TEXT
*   **Length:** 50-500 characters
*   **Required:** Yes
*   **Format:** Clear instructional text
*   **Validation:** Must clearly explain what user should do

#### `exercise_input` Field
*   **Data Type:** TEXT
*   **Length:** 50-1000 characters (varies by type)
*   **Required:** Yes
*   **Format:** Type-specific (see above)
*   **Validation:** Must match exercise type requirements

#### `expected_output` Field
*   **Data Type:** TEXT
*   **Length:** 3-500 characters
*   **Required:** Yes
*   **Format:** Single answer or short response
*   **Validation:** Must be the correct answer for the given input

---

## 4. Conversation & Memory

### 4.1 `conversation_logs`
Raw history for context window retrieval.
*   `id`: **BIGINT** (PK, Auto-increment for sorting)
*   `user_id`: **UUID** (FK -> users.id)
*   `role`: **ENUM** ('user', 'assistant', 'system').
*   `content`: **TEXT** - The message body.
*   `message_type`: **ENUM** ('text', 'audio', 'image', 'template').
*   `created_at`: **TIMESTAMP** - Index this for fast retrieval of "last 10 messages".
*   `whatsapp_message_id`: **VARCHAR(100)** - To prevent processing duplicates.

---

## 5. Progress & Analytics

### 5.1 `user_exercise_history`
Logs every attempt a user makes.
*   `id`: **UUID** (PK)
*   `user_id`: **UUID** (FK)
*   `exercise_id`: **UUID** (FK)
*   `user_input`: **TEXT** - What they typed/said.
*   `is_correct`: **BOOLEAN** - Result of the Judge.
*   `judge_feedback`: **TEXT** - The explanation given to the user.
*   `response_time_ms`: **INTEGER** - How long they took to reply.
*   `created_at`: **TIMESTAMP**.

### 5.2 `user_mastery`
Aggregated scores to track "Strength".
*   `user_id`: **UUID** (FK)
*   `topic_id`: **UUID** (FK)
*   `mastery_score`: **FLOAT** (0.0 to 1.0).
*   `last_practiced_at`: **TIMESTAMP**.

### 5.3 `daily_stats` (For Limits & Streaks)
*   `user_id`: **UUID** (FK)
*   `date`: **DATE**
*   `messages_sent`: **INTEGER**
*   `lessons_completed`: **INTEGER**
*   `streak_active`: **BOOLEAN**

---

## 6. Monetization (Stripe)

### 6.1 `subscriptions`
*   `user_id`: **UUID** (PK) - One-to-one relationship.
*   `stripe_customer_id`: **VARCHAR(100)**.
*   `stripe_subscription_id`: **VARCHAR(100)**.
*   `plan_type`: **ENUM** ('free', 'monthly_pro', 'annual_pro').
*   `status`: **ENUM** ('active', 'past_due', 'canceled', 'trialing').
*   `current_period_end`: **TIMESTAMP**.
*   `cancel_at_period_end`: **BOOLEAN**.

---

## 7. Growth & Experiments

### 7.1 `experiments`
*   `id`: **VARCHAR(50)** (PK) - e.g., "strict-tutor-v1".
*   `description`: **TEXT**.
*   `status`: **ENUM** ('active', 'paused').

### 7.2 `experiment_assignments`
*   `user_id`: **UUID** (FK)
*   `experiment_id`: **VARCHAR(50)** (FK)
*   `variant`: **VARCHAR(10)** - 'A' or 'B'.
*   `assigned_at`: **TIMESTAMP**.

---

## 8. Redis Schema (Ephemeral Data)
Used for high-speed checks and rate limiting.

*   **Rate Limits:** `limit:msg:{user_id}` -> `Integer` (TTL: 24h).
*   **Conversation State:** `session:{user_id}` -> `JSON`
    ```json
    {
      "current_flow": "onboarding",
      "step": "question_2",
      "temp_data": { "correct_count": 1 }
    }
    ```
*   **Typ**