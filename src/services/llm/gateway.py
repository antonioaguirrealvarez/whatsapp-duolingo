"""LLM Gateway for unified model interface with OpenAI integration."""

import logging
from typing import Any, Dict, List, Optional
import asyncio

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langsmith import Client as LangSmithClient

from core.config import get_settings
from core.exceptions import LLMError, OpenAIError

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMGateway:
    """Unified gateway for LLM operations with OpenAI integration."""
    
    def __init__(self):
        """Initialize the LLM gateway."""
        try:
            self.settings = get_settings()
            
            # Initialize models for different use cases
            self.fast_model = ChatOpenAI(
                api_key=self.settings.OPENAI_API_KEY,
                model="gpt-4o-mini",  # Fast model for content generation and evaluation
                temperature=0.7,
                max_tokens=1000,
            )
            
            self.smart_model = ChatOpenAI(
                api_key=self.settings.OPENAI_API_KEY,
                model="gpt-4o",  # More capable model when needed
                temperature=0.7,
                max_tokens=1000,
            )
            
            # Default to fast model
            self.model = self.fast_model
            
            # Initialize LangSmith if enabled
            self.langsmith_client = None
            if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
                try:
                    self.langsmith_client = LangSmithClient(
                        api_url=settings.LANGSMITH_ENDPOINT,
                        api_key=settings.LANGSMITH_API_KEY
                    )
                    logger.info("LangSmith tracing enabled")
                except Exception as e:
                    logger.warning(f"Failed to initialize LangSmith: {e}")
            
            logger.info(f"LLM Gateway initialized with model: {settings.OPENAI_MODEL}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM Gateway: {e}")
            raise LLMError(f"Failed to initialize gateway: {e}")
    
    async def get_response(
        self, 
        user_text: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Get a response from the LLM.
        
        Args:
            user_text: User input text
            conversation_history: Optional conversation history
            system_prompt: Optional system prompt
            
        Returns:
            LLM response text
            
        Raises:
            LLMError: If LLM request fails
        """
        try:
            # Build message list
            messages: List[BaseMessage] = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    
                    if role == "system":
                        messages.append(SystemMessage(content=content))
                    elif role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            
            # Add current user message
            messages.append(HumanMessage(content=user_text))
            
            logger.info(f"Sending request to LLM with {len(messages)} messages")
            
            # Get response from LLM
            response = await self.model.ainvoke(messages)
            
            response_text = response.content
            logger.info(f"Received LLM response: {response_text[:100]}...")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            raise LLMError(f"Failed to get LLM response: {e}")
    
    def invoke(self, prompt: str, model_type: str = "fast") -> str:
        """
        Synchronous invoke method for LLM calls.
        
        Args:
            prompt: Input prompt for LLM
            model_type: Type of model to use ("fast" or "smart")
            
        Returns:
            LLM response text
            
        Raises:
            LLMError: If LLM request fails
        """
        try:
            # Select model based on type
            if model_type == "smart":
                model = self.smart_model
            else:
                model = self.fast_model
            
            # Use the synchronous LangChain method
            messages = [HumanMessage(content=prompt)]
            response = model.invoke(messages)
            response_text = response.content
            logger.info(f"Received LLM response: {response_text[:100]}...")
            return response_text
        except Exception as e:
            logger.error(f"Error in synchronous invoke: {e}")
            raise LLMError(f"Failed to invoke LLM: {e}")
    
    async def get_structured_output(
        self,
        prompt: str,
        output_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get structured output from the LLM.
        
        Args:
            prompt: Input prompt
            output_schema: Optional output schema for structured output
            
        Returns:
            Structured response as dictionary
            
        Raises:
            LLMError: If LLM request fails
        """
        try:
            # For now, we'll use regular text response and try to parse as JSON
            # In a full implementation, we'd use structured output features
            
            messages = [HumanMessage(content=prompt)]
            
            logger.info("Sending structured output request to LLM")
            
            response = await self.model.ainvoke(messages)
            response_text = response.content
            
            # Try to parse as JSON
            try:
                import json
                structured_response = json.loads(response_text)
                return structured_response
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                return {"response": response_text}
                
        except Exception as e:
            logger.error(f"Error getting structured output: {e}")
            raise LLMError(f"Failed to get structured output: {e}")
    
    async def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        correct_answer: str,
        rubric: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a user's answer using the LLM.
        
        Args:
            question: The question asked
            user_answer: User's answer
            correct_answer: The correct answer
            rubric: Optional evaluation rubric
            
        Returns:
            Evaluation result with is_correct, feedback, etc.
        """
        try:
            evaluation_prompt = f"""
            You are an expert language tutor. Evaluate the student's answer:
            
            Question: {question}
            Student's Answer: {user_answer}
            Correct Answer: {correct_answer}
            
            {"Rubric: " + rubric if rubric else ""}
            
            Provide your evaluation in JSON format:
            {{
                "is_correct": true/false,
                "score": 0.0-1.0,
                "feedback": "Brief, encouraging feedback",
                "error_type": "grammar/vocabulary/spelling/none",
                "suggestion": "How to improve"
            }}
            """
            
            result = await self.get_structured_output(evaluation_prompt)
            
            # Ensure required fields
            if "is_correct" not in result:
                result["is_correct"] = False
            if "score" not in result:
                result["score"] = 0.0
            if "feedback" not in result:
                result["feedback"] = "Keep practicing!"
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating answer: {e}")
            raise LLMError(f"Failed to evaluate answer: {e}")
    
    async def generate_exercise(
        self,
        topic: str,
        difficulty: str,
        exercise_type: str,
        target_language: str = "English",
        native_language: str = "Spanish"
    ) -> Dict[str, Any]:
        """
        Generate a language learning exercise.
        
        Args:
            topic: Exercise topic (e.g., "ordering food")
            difficulty: Difficulty level (A1, A2, B1, etc.)
            exercise_type: Type of exercise (multiple_choice, fill_blank, etc.)
            target_language: Language being learned
            native_language: User's native language
            
        Returns:
            Generated exercise data
        """
        try:
            exercise_prompt = f"""
            Generate a {difficulty} level {exercise_type} exercise for {native_language} speakers learning {target_language}.
            
            Topic: {topic}
            
            Generate the exercise in JSON format:
            {{
                "question": "The exercise question",
                "correct_answer": "The correct answer",
                "options": ["option1", "option2", "option3", "option4"],
                "explanation": "Why this is the correct answer",
                "difficulty": "{difficulty}",
                "topic": "{topic}",
                "exercise_type": "{exercise_type}"
            }}
            """
            
            result = await self.get_structured_output(exercise_prompt)
            
            # Ensure required fields
            required_fields = ["question", "correct_answer", "explanation"]
            for field in required_fields:
                if field not in result:
                    result[field] = "Not provided"
            
            if exercise_type == "multiple_choice" and "options" not in result:
                result["options"] = [result["correct_answer"], "Option 2", "Option 3", "Option 4"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating exercise: {e}")
            raise LLMError(f"Failed to generate exercise: {e}")
    
    def trace_run(self, run_name: str, inputs: Dict[str, Any], outputs: Dict[str, Any]):
        """
        Trace a run in LangSmith if enabled.
        
        Args:
            run_name: Name of the run
            inputs: Input data
            outputs: Output data
        """
        if self.langsmith_client:
            try:
                # This is a simplified tracing implementation
                # In a full implementation, we'd use LangSmith's proper tracing
                logger.info(f"Tracing run: {run_name}")
                # TODO: Implement proper LangSmith tracing
            except Exception as e:
                logger.warning(f"Failed to trace run: {e}")


# Global gateway instance
llm_gateway = LLMGateway()
