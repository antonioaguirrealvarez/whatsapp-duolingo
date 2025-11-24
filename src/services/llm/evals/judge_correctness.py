"""Correctness evaluator for assessing user responses using LLM-as-a-Judge."""

import asyncio
import json
import logging
from typing import Dict, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class CorrectnessEvaluator:
    """Evaluates user response correctness using structured LLM output."""
    
    def __init__(self, model: Optional[ChatOpenAI] = None):
        """Initialize the evaluator with an OpenAI model."""
        self.settings = get_settings()
        self.model = model or ChatOpenAI(
            model=self.settings.OPENAI_MODEL,
            temperature=0.1,  # Low temperature for consistent evaluation
        )
        self.parser = JsonOutputParser()
        self.chain = self._create_evaluation_chain()
    
    def _create_evaluation_chain(self):
        """Create the LangChain evaluation pipeline."""
        template = """
You are an expert language teacher evaluating a student's response.

Question: {question}
Expected Answer Type: {rubric}
Student's Answer: {user_answer}

Evaluate the response and provide a JSON assessment with the following structure:
{{
    "is_correct": boolean,
    "error_type": string|null,
    "feedback_key": string|null,
    "confidence": float (0.0-1.0),
    "explanation": string (brief explanation for the teacher)
}}

Error types to use:
- "grammar" - grammatical errors (verb conjugation, tense, etc.)
- "vocabulary" - wrong word choice
- "spelling" - spelling mistakes
- "syntax" - word order issues
- "comprehension" - misunderstood the question
- "none" - if the answer is correct

Feedback keys should be specific and actionable:
- "verb_conjugation" - for verb tense errors
- "subject_agreement" - for subject-verb agreement
- "word_choice" - for vocabulary issues
- "spelling_correction" - for spelling errors
- "word_order" - for syntax issues

Be thorough but fair. Focus on the most significant error if multiple exist.
"""
        
        prompt = PromptTemplate(
            input_variables=["question", "user_answer", "rubric"],
            template=template,
        )
        
        return (
            {"question": RunnablePassthrough(), "user_answer": RunnablePassthrough(), "rubric": RunnablePassthrough()}
            | prompt
            | self.model
            | self.parser
        )
    
    async def evaluate_response(
        self,
        question: str,
        user_answer: str,
        rubric: str = "general language response"
    ) -> Dict:
        """
        Evaluate a user's response to a question.
        
        Args:
            question: The question asked to the user
            user_answer: The user's response
            rubric: Type of response expected (helps guide evaluation)
            
        Returns:
            Dict containing evaluation results with keys:
            - is_correct: bool
            - error_type: str or null
            - feedback_key: str or null
            - confidence: float
            - explanation: str
        """
        try:
            logger.info(f"Evaluating response: '{user_answer}' to question: '{question}'")
            
            result = await self.chain.ainvoke({
                "question": question,
                "user_answer": user_answer,
                "rubric": rubric,
            })
            
            # Validate the output structure
            evaluation = result
            if not isinstance(evaluation, dict):
                logger.error(f"Invalid evaluation format: {evaluation}")
                return self._get_fallback_evaluation()
            
            # Ensure required fields exist
            required_fields = ["is_correct", "error_type", "feedback_key", "confidence", "explanation"]
            for field in required_fields:
                if field not in evaluation:
                    logger.warning(f"Missing field '{field}' in evaluation result")
                    evaluation[field] = None if field != "is_correct" else False
            
            logger.info(f"Evaluation completed: is_correct={evaluation.get('is_correct')}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error during evaluation: {str(e)}")
            return self._get_fallback_evaluation()
    
    def _get_fallback_evaluation(self) -> Dict:
        """Return a safe fallback evaluation when LLM fails."""
        return {
            "is_correct": False,
            "error_type": "comprehension",
            "feedback_key": "evaluation_error",
            "confidence": 0.0,
            "explanation": "Unable to evaluate response due to system error"
        }
    
    async def batch_evaluate(
        self,
        responses: list[Dict[str, str]]
    ) -> list[Dict]:
        """
        Evaluate multiple responses in parallel.
        
        Args:
            responses: List of dicts with 'question', 'user_answer', 'rubric' keys
            
        Returns:
            List of evaluation results
        """
        tasks = [
            self.evaluate_response(
                question=r["question"],
                user_answer=r["user_answer"],
                rubric=r.get("rubric", "general language response")
            )
            for r in responses
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)


# Singleton instance for easy import (lazy initialization)
evaluator = None

def get_evaluator() -> CorrectnessEvaluator:
    """Get the singleton evaluator instance."""
    global evaluator
    if evaluator is None:
        evaluator = CorrectnessEvaluator()
    return evaluator
