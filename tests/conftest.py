import pytest
import asyncio
import logging
from unittest.mock import patch
from typing import Any, Dict

# Import the audit logger directly
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from audit_logger import audit_logger

# Import classes to patch
from src.services.llm.gateway import LLMGateway
from src.services.llm.content_generation import ContentGenerationAgent
from src.services.llm.evals.judge_correctness import CorrectnessEvaluator
from src.services.llm.evals.judge_tone import ToneEvaluator

@pytest.fixture(scope="session", autouse=True)
def setup_audit_logger():
    """Initialize the audit logger at the start of the test session."""
    audit_logger.log_event("Test Session Started", "Running tests with audit logging enabled.")
    yield
    audit_logger.log_event("Test Session Ended", "Tests completed.")

@pytest.fixture(autouse=True)
def audit_llm_calls():
    """
    Spy on LLM service methods to log inputs and outputs to the audit log
    without interfering with the actual execution (integration tests still use real APIs).
    """
    
    # 1. Patch LLMGateway.get_response
    original_get_response = LLMGateway.get_response
    
    async def audited_get_response(self, user_text: str, *args, **kwargs):
        input_data = {"user_text": user_text, "args": args, "kwargs": kwargs}
        try:
            result = await original_get_response(self, user_text, *args, **kwargs)
            audit_logger.log_llm_interaction("LLMGateway.get_response", input_data, result)
            return result
        except Exception as e:
            audit_logger.log_llm_interaction("LLMGateway.get_response (FAILED)", input_data, str(e))
            raise e

    # 2. Patch ContentGenerationAgent.generate_exercises
    original_generate_exercises = ContentGenerationAgent.generate_exercises
    
    async def audited_generate_exercises(self, source_lang, target_lang, difficulty, exercise_type, topic, *args, **kwargs):
        input_data = {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "difficulty": str(difficulty),
            "exercise_type": str(exercise_type),
            "topic": topic,
            "kwargs": kwargs
        }
        try:
            # Note: result is usually a list of exercises or similar
            result = await original_generate_exercises(self, source_lang, target_lang, difficulty, exercise_type, topic, *args, **kwargs)
            audit_logger.log_llm_interaction("ContentGenerationAgent.generate_exercises", input_data, f"Generated {len(result) if isinstance(result, list) else 'unknown'} items")
            return result
        except Exception as e:
            audit_logger.log_llm_interaction("ContentGenerationAgent.generate_exercises (FAILED)", input_data, str(e))
            raise e

    # 3. Patch CorrectnessEvaluator.evaluate_response
    original_evaluate_response = CorrectnessEvaluator.evaluate_response
    
    async def audited_evaluate_response(self, question, user_answer, rubric="general language response", *args, **kwargs):
        input_data = {"question": question, "user_answer": user_answer, "rubric": rubric}
        try:
            result = await original_evaluate_response(self, question, user_answer, rubric, *args, **kwargs)
            audit_logger.log_llm_interaction("CorrectnessEvaluator.evaluate_response", input_data, result)
            return result
        except Exception as e:
            audit_logger.log_llm_interaction("CorrectnessEvaluator.evaluate_response (FAILED)", input_data, str(e))
            raise e
            
    # Apply patches using patch.object with proper binding
    p1 = patch.object(LLMGateway, 'get_response', audited_get_response)
    p2 = patch.object(ContentGenerationAgent, 'generate_exercises', audited_generate_exercises)
    p3 = patch.object(CorrectnessEvaluator, 'evaluate_response', audited_evaluate_response)
    
    with p1, p2, p3:
        yield
