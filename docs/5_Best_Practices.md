# 📚 ENGINEERING BEST PRACTICES & CODE STANDARD
**Project:** WhatsApp-First AI Language Tutor
**Role:** CTO Guidelines
**Status:** Living Document

---

## 1. The "Golden Rule" (Philosophy)
> "Code is read 10x more often than it is written. Write for the reader, not the compiler."

We value **clarity over cleverness**. If a junior engineer cannot understand your code in 30 seconds, it is bad code, no matter how optimized it is.

---

## 2. Coding Standards & Style

### 2.1 Typing & Validation
*   **Strict Typing:** All functions MUST have type hints. No `Any` allowed unless absolutely necessary (and commented why).
    ```python
    # ❌ BAD
    def process_data(data):
        return data['key']

    # ✅ GOOD
    def process_data(data: Dict[str, Any]) -> str:
        return data.get('key', '')
    ```
*   **Pydantic Everywhere:** Do not pass raw dictionaries between layers (e.g., from API to Logic). Convert them to `Pydantic` models immediately at the boundary.

### 2.2 Naming Conventions
*   **Variables:** `snake_case`. Be descriptive. `user_id` > `uid`. `daily_lesson_count` > `cnt`.
*   **Classes:** `PascalCase`. Nouns. `UserSession`, `PaymentProcessor`.
*   **Functions:** `snake_case`. Verbs first. `calculate_score()`, `fetch_user_data()`.
*   **Booleans:** Start with `is_`, `has_`, `can_`. `is_premium`, `has_completed_onboarding`.

### 2.3 Function Structure
*   **Max Length:** If a function is > 50 lines, break it down.
*   **Arguments:** If a function takes > 3 arguments, use a Pydantic model or Dataclass as the input.
    ```python
    # ❌ BAD
    def create_user(name, age, email, phone, level, country): ...

    # ✅ GOOD
    def create_user(profile: UserProfileCreate): ...
    ```
*   **Docstrings:** Mandatory for all public functions. Use Google Style.
    ```python
    def calculate_xp(correct_answers: int, streak: int) -> int:
        """Calculates XP based on performance and multipliers.

        Args:
            correct_answers: Number of correct responses.
            streak: Current day streak.

        Returns:
            Total XP integer.
        """
    ```

---

## 3. Architecture & Modularity

### 3.1 The "Layer Cake" Rule
*   **Dependencies flow DOWN.**
    *   `API` can import `Services`.
    *   `Services` can import `Data`.
    *   `Data` CANNOT import `API` or `Services`.
*   **Circular Imports:** Are a sign of bad architecture. If A imports B and B imports A, create a third module C that both share.

### 3.2 Service Isolation
*   **Single Responsibility:** The `PaymentService` should not know how to `SendWhatsAppMessage`. It should return a result, and the `Orchestrator` should decide to send a message.
*   **Configuration:** Never hardcode secrets or configs inside functions. Use `core/config.py` (Environment Variables).

---

## 4. Error Handling & Logging

### 4.1 Defensive Programming
*   **Catch Specific Errors:** Never use bare `except:`. Catch `ValueError`, `NetworkError`, etc.
*   **Fail Fast:** Validate inputs at the start of the function.
*   **Custom Exceptions:** Create domain-specific exceptions in `core/exceptions.py`.
    *   `UserNotPremiumError`
    *   `WhatsAppRateLimitError`

### 4.2 Centralized Logging
*   **No Print Statements:** use `logger.info()`, `logger.warning()`, `logger.error()`.
*   **Structured Logging:** Logs should be machine-readable (JSON in prod) and contain context.
    ```python
    # ✅ GOOD
    logger.info("Processing payment", extra={"user_id": user.id, "amount": 500})
    ```
*   **Log Levels:**
    *   `DEBUG`: Granular info for local dev (payloads, internal steps).
    *   `INFO`: High-level flow (e.g., "User completed lesson").
    *   `WARNING`: Handled errors (e.g., "Webhook retry triggered").
    *   `ERROR`: Unhandled exceptions or critical failures.

---

## 5. Testing Strategy

### 5.1 The Testing Pyramid
1.  **Unit Tests (70%):** Test individual functions in isolation. Mock DB and LLM calls.
    *   *Tool:* `pytest`
    *   *Naming:* `test_<function_name>_<condition>`. Example: `test_calculate_score_with_perfect_streak`.
    *   *Pattern:* AAA (Arrange, Act, Assert).
2.  **Integration Tests (20%):** Test interaction between Service and DB. (e.g., "Create User" actually saves to SQL).
3.  **E2E Tests (10%):** Full flow. "User sends msg -> Webhook receives -> LLM replies -> Msg sent back."

### 5.2 LLM Testing (The "Vibe Check")
*   **Deterministic Tests:** Mock the LLM response to test your logic (parsing JSON, handling errors).
*   **Evals (LangSmith):** Run "Golden Datasets" weekly to ensure prompt changes didn't degrade quality.

### 5.3 Integration Test Logging (API & LLM Audit Trail)
*   **Log All External API Calls:** Every integration test that calls LLMs or critical external APIs MUST log inputs and outputs to a dedicated audit file.
*   **Audit File Structure:** Create timestamped log files in `tests/logs/integration_audit/` with format `YYYY-MM-DD_HH-mm-ss_{test_name}.jsonl`
*   **Log Content:** Each log entry must include:
    ```json
    {
        "timestamp": "2025-01-15T10:30:45Z",
        "test_name": "test_openai_lesson_generation",
        "api_endpoint": "openai.chat.completions.create",
        "request": {"model": "gpt-4", "messages": [...], "temperature": 0.7},
        "response": {"choices": [...], "usage": {...}},
        "duration_ms": 1250,
        "success": true
    }
    ```
*   **PII Redaction:** Automatically scrub sensitive data (phone numbers, personal info) before logging. Use `core/security.py:redact_pii()`.
*   **Automated Cleanup:** Keep only last 30 days of audit logs. Configure in `pytest.ini` or test setup.
*   **Manual Review Process:** Weekly review of audit logs required before deploying prompt changes or API integrations.

---

## 6. Git & Version Control

### 6.1 Commit Messages
*   **Format:** `[TYPE] Short description`
    *   `[FEAT] Add stripe checkout`
    *   `[FIX] Resolve webhook timeout`
    *   `[DOCS] Update PRD`
    *   `[REFACTOR] Simplify router logic`

### 6.2 Pull Requests
*   **Review Rule:** No PR is merged without at least 1 approval.
*   **CI/CD:** All tests must pass before merge. Linting (`ruff` or `black`) is enforced automatically.

### 6.3 Repository Hygiene (No Vestigial Files)
*   **Delete Temp Scripts:** Do not commit `test_script.py`, `temp.json`, or `adhoc_fix.py`. If you need a script for a one-off task, put it in `scripts/` or delete it after use.
*   **Clean Up Branches:** Delete feature branches after they are merged.
*   **No Commented-Out Code:** Do not leave blocks of commented-out code "just in case". That's what Git history is for.

---

## 7. Documentation

### 7.1 Code Documentation
*   **Self-Documenting Code:** Clear variable names are better than comments.
*   **The "Why", not the "What":** Comments should explain *why* you made a complex decision, not what the code is doing (unless it's regex).
*   **Ubiquitous Language (Glossary):** Use consistent terms across the codebase, PRD, and conversations.
    *   *User:* The person chatting on WhatsApp.
    *   *Session:* The active conversation window (24h).
    *   *Lesson:* A single learning unit consisting of exercises.
    *   *Drill:* A specific question within a lesson.

### 7.2 API Docs
*   **OpenAPI:** FastAPI generates OpenAPI docs automatically. Keep Pydantic descriptions rich so these docs are useful.

---

## 8. LLM Engineering & Prompt Management
*   **No Hardcoded Prompts:** Never put prompt strings inside Python code. Use Jinja2 templates in `src/services/llm/prompts/`.
*   **Prompt Versioning:** Treat prompts like code. When changing a prompt, update the version or add a comment.
*   **Eval-Driven Development:** Do not deploy a prompt change without running it against the "Golden Dataset" in LangSmith.
*   **Hallucination Guardrails:** Always assume the LLM will lie. Validate structured output (JSON) with Pydantic before using it.

---

## 9. Security & Privacy
*   **No Secrets in Code:** `.env` files are for local development only. In production, use a Secret Manager.
*   **PII Scrubbing:** Never log user phone numbers or messages in plain text unless necessary for debugging (and scrub them in prod).
*   **Input Sanitization:** Although ORMs handle SQL injection, be careful with "Prompt Injection". Sanitize user input before sending it to the LLM (e.g., strip system instructions).

---

## 10. Async & Performance Hygiene
*   **Don't Block the Event Loop:** Never use blocking I/O (e.g., `requests`, `time.sleep`) inside an `async def`. Use `httpx` and `asyncio.sleep`.
*   **Database Pooling:** Always use connection pooling (SQLAlchemy async engine) to avoid exhausting DB connections.
*   **Fire & Forget:** For heavy tasks (like generating a lesson), push to a Queue (Redis/Celery) instead of awaiting it in the API response.

---

## 11. Dependency Management
*   **Deterministic Builds:** Always commit `poetry.lock`. This ensures every developer and the production server use the exact same package versions.
*   **Keep it Light:** Do not add heavy libraries (like `pandas` or `numpy`) unless strictly necessary. Use built-in Python structures where possible.