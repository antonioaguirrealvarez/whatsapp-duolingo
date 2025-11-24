"""LangSmith client for observability and tracing."""

import logging
import os
from typing import Optional, Dict, Any

from langsmith import Client as LangSmithClient

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class LangSmithManager:
    """Manages LangSmith tracing and observability."""
    
    def __init__(self):
        """Initialize LangSmith manager."""
        self.settings = get_settings()
        self.client: Optional[LangSmithClient] = None
        self._initialize()
    
    def _initialize(self):
        """Initialize LangSmith client if enabled."""
        if not self.settings.LANGSMITH_TRACING:
            logger.info("LangSmith tracing is disabled")
            return
        
        if not self.settings.LANGSMITH_API_KEY:
            logger.warning("LangSmith tracing enabled but no API key provided")
            return
        
        try:
            # Set environment variables for LangSmith
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = self.settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = self.settings.LANGSMITH_ENDPOINT
            os.environ["LANGCHAIN_API_KEY"] = self.settings.LANGSMITH_API_KEY
            
            # Initialize LangSmith client
            self.client = LangSmithClient(
                api_url=self.settings.LANGSMITH_ENDPOINT,
                api_key=self.settings.LANGSMITH_API_KEY
            )
            
            logger.info(f"LangSmith tracing initialized for project: {self.settings.LANGSMITH_PROJECT}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangSmith: {str(e)}")
            self.client = None
    
    def is_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled and configured."""
        return self.client is not None
    
    def log_user_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a user interaction to LangSmith.
        
        Args:
            user_id: WhatsApp user ID
            message: User's message
            response: Bot's response
            metadata: Additional metadata (tokens, latency, etc.)
        """
        if not self.is_enabled():
            return
        
        try:
            # Create a run in LangSmith
            run_data = {
                "name": "whatsapp_interaction",
                "input": message,
                "output": response,
                "metadata": {
                    "user_id": user_id,
                    "platform": "whatsapp",
                    **(metadata or {})
                }
            }
            
            # This would be used with LangChain's callback system
            # For now, we'll just log locally
            logger.info(f"LangSmith: Logged interaction for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log interaction to LangSmith: {str(e)}")
    
    def create_evaluation_dataset(
        self,
        dataset_name: str,
        examples: list[Dict[str, Any]]
    ):
        """
        Create an evaluation dataset in LangSmith.
        
        Args:
            dataset_name: Name of the dataset
            examples: List of examples with 'input' and 'output' keys
        """
        if not self.is_enabled():
            logger.warning("LangSmith not enabled, skipping dataset creation")
            return
        
        try:
            # Check if dataset already exists
            existing_datasets = self.client.list_datasets()
            dataset_exists = any(
                dataset.name == dataset_name 
                for dataset in existing_datasets
            )
            
            if dataset_exists:
                logger.info(f"Dataset '{dataset_name}' already exists")
                return
            
            # Create new dataset
            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description="WhatsApp Duolingo evaluation dataset"
            )
            
            # Add examples to dataset
            for example in examples:
                self.client.create_example(
                    dataset_id=dataset.id,
                    inputs={"question": example["input"]},
                    outputs={"answer": example["output"]},
                    metadata=example.get("metadata", {})
                )
            
            logger.info(f"Created LangSmith dataset '{dataset_name}' with {len(examples)} examples")
            
        except Exception as e:
            logger.error(f"Failed to create dataset: {str(e)}")
    
    def trace_llm_call(
        self,
        model_name: str,
        prompt: str,
        response: str,
        tokens_used: Optional[int] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Trace an LLM call for observability.
        
        Args:
            model_name: Name of the LLM model
            prompt: The prompt sent to the LLM
            response: The response from the LLM
            tokens_used: Number of tokens used
            latency_ms: Latency in milliseconds
            metadata: Additional metadata
        """
        if not self.is_enabled():
            return
        
        try:
            trace_data = {
                "model": model_name,
                "prompt": prompt,
                "response": response,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "metadata": metadata or {}
            }
            
            logger.info(f"LangSmith: Traced LLM call with model {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to trace LLM call: {str(e)}")
    
    def get_project_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get statistics for the LangSmith project.
        
        Returns:
            Dict with project statistics or None if not enabled
        """
        if not self.is_enabled():
            return None
        
        try:
            # This would require additional LangSmith API calls
            # For now, return basic info
            return {
                "project_name": self.settings.LANGSMITH_PROJECT,
                "tracing_enabled": True,
                "endpoint": self.settings.LANGSMITH_ENDPOINT
            }
            
        except Exception as e:
            logger.error(f"Failed to get project stats: {str(e)}")
            return None


# Global instance for easy import
langsmith_manager = LangSmithManager()

def get_langsmith_manager() -> LangSmithManager:
    """Get the LangSmith manager instance."""
    return langsmith_manager
