"""Tone and style evaluator for assessing bot response virality."""

import asyncio
import logging
from typing import Dict, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class ToneEvaluator:
    """Evaluates bot response tone and style to ensure engaging conversations."""
    
    def __init__(self, model: Optional[ChatOpenAI] = None):
        """Initialize the evaluator with an OpenAI model."""
        self.settings = get_settings()
        self.model = model or ChatOpenAI(
            model=self.settings.OPENAI_MODEL,
            temperature=0.3,  # Moderate temperature for creative evaluation
        )
        self.parser = JsonOutputParser()
        self.chain = self._create_evaluation_chain()
    
    def _create_evaluation_chain(self):
        """Create the LangChain evaluation pipeline."""
        template = """
You are an expert conversation analyst evaluating a language tutor's response style.

Bot Response: "{bot_response}"

Evaluate the response on a scale of 1-10 for virality and engagement. Consider:
- Personality and sassiness (not boring)
- Cultural relevance and slang usage
- Encouragement and motivation
- Conversational flow
- Humor and wit

Provide a JSON assessment with the following structure:
{{
    "virality_score": float (1.0-10.0),
    "personality_score": float (1.0-10.0),
    "engagement_score": float (1.0-10.0),
    "is_boring": boolean,
    "feedback": string (brief explanation of the score),
    "improvement_suggestions": string|null (how to make it more engaging)
}}

Scoring guidelines:
- 9-10: Highly engaging, viral-worthy content
- 7-8: Good, engaging but could be better
- 5-6: Average, somewhat boring
- 1-4: Very boring, needs complete rewrite

Be honest but constructive. The goal is to create a tutor that users love talking to.
"""
        
        prompt = PromptTemplate(
            input_variables=["bot_response"],
            template=template,
        )
        
        return (
            {"bot_response": RunnablePassthrough()}
            | prompt
            | self.model
            | self.parser
        )
    
    async def assess_virality(self, bot_response: str) -> Dict:
        """
        Assess the virality and engagement level of a bot response.
        
        Args:
            bot_response: The bot's response text to evaluate
            
        Returns:
            Dict containing evaluation results with keys:
            - virality_score: float (1.0-10.0)
            - personality_score: float (1.0-10.0)
            - engagement_score: float (1.0-10.0)
            - is_boring: bool
            - feedback: str
            - improvement_suggestions: str or null
        """
        try:
            logger.info(f"Assessing virality of response: '{bot_response[:100]}...'")
            
            result = await self.chain.ainvoke({
                "bot_response": bot_response,
            })
            
            # Validate the output structure
            evaluation = result
            if not isinstance(evaluation, dict):
                logger.error(f"Invalid evaluation format: {evaluation}")
                return self._get_fallback_evaluation()
            
            # Ensure required fields exist
            required_fields = ["virality_score", "personality_score", "engagement_score", "is_boring", "feedback", "improvement_suggestions"]
            for field in required_fields:
                if field not in evaluation:
                    logger.warning(f"Missing field '{field}' in evaluation result")
                    if field == "is_boring":
                        # Don't set yet, will calculate based on virality_score
                        pass
                    elif "score" in field:
                        evaluation[field] = 5.0
                    else:
                        evaluation[field] = None
            
            # Set is_boring based on virality_score
            if "is_boring" not in evaluation or evaluation["is_boring"] is None:
                evaluation["is_boring"] = evaluation.get("virality_score", 5.0) < 7.0
            
            logger.info(f"Virality assessment completed: score={evaluation.get('virality_score')}, boring={evaluation.get('is_boring')}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error during virality assessment: {str(e)}")
            return self._get_fallback_evaluation()
    
    async def should_regenerate(self, bot_response: str, threshold: float = 7.0) -> tuple[bool, Dict]:
        """
        Determine if a response should be regenerated based on its virality score.
        
        Args:
            bot_response: The bot's response text to evaluate
            threshold: Minimum virality score to avoid regeneration
            
        Returns:
            Tuple of (should_regenerate: bool, evaluation: Dict)
        """
        evaluation = await self.assess_virality(bot_response)
        virality_score = evaluation.get("virality_score", 5.0)
        
        should_regenerate = virality_score < threshold
        logger.info(f"Regeneration decision: {should_regenerate} (score: {virality_score}, threshold: {threshold})")
        
        return should_regenerate, evaluation
    
    async def suggest_improvements(self, bot_response: str) -> Optional[str]:
        """
        Get specific suggestions to improve a boring response.
        
        Args:
            bot_response: The bot's response text to improve
            
        Returns:
            String with improvement suggestions or None if response is good
        """
        evaluation = await self.assess_virality(bot_response)
        return evaluation.get("improvement_suggestions")
    
    def _get_fallback_evaluation(self) -> Dict:
        """Return a safe fallback evaluation when LLM fails."""
        return {
            "virality_score": 5.0,
            "personality_score": 5.0,
            "engagement_score": 5.0,
            "is_boring": True,
            "feedback": "Unable to assess tone due to system error",
            "improvement_suggestions": "Add more personality and engagement to the response"
        }
    
    async def batch_assess(self, responses: list[str]) -> list[Dict]:
        """
        Assess multiple responses in parallel.
        
        Args:
            responses: List of bot response strings
            
        Returns:
            List of evaluation results
        """
        tasks = [self.assess_virality(response) for response in responses]
        return await asyncio.gather(*tasks, return_exceptions=True)


# Singleton instance for easy import (lazy initialization)
evaluator = None

def get_tone_evaluator() -> ToneEvaluator:
    """Get the singleton tone evaluator instance."""
    global evaluator
    if evaluator is None:
        evaluator = ToneEvaluator()
    return evaluator
