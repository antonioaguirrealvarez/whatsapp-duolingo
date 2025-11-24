"""Prompt manager for dynamic template rendering."""

import logging
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, Template

from src.core.exceptions import LLMError

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages and renders prompt templates using Jinja2."""
    
    def __init__(self, template_dir: str = "src/services/llm/prompts/templates"):
        """Initialize the prompt manager."""
        try:
            # Set up Jinja2 environment
            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            # Cache for loaded templates
            self._template_cache: Dict[str, Template] = {}
            
            logger.info("Prompt manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize prompt manager: {e}")
            raise LLMError(f"Failed to initialize prompt manager: {e}")
    
    def render_prompt(
        self, 
        template_name: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Render a prompt template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Variables to inject into the template
            
        Returns:
            Rendered prompt text
            
        Raises:
            LLMError: If template rendering fails
        """
        try:
            # Load template (with caching)
            template = self._get_template(template_name)
            
            # Render with context
            rendered = template.render(**context)
            
            logger.info(f"Rendered template: {template_name}")
            return rendered
            
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise LLMError(f"Failed to render template: {e}")
    
    def _get_template(self, template_name: str) -> Template:
        """
        Get a template from cache or load it.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Jinja2 Template object
        """
        if template_name not in self._template_cache:
            try:
                self._template_cache[template_name] = self.env.get_template(template_name)
            except Exception as e:
                logger.error(f"Failed to load template {template_name}: {e}")
                raise LLMError(f"Template not found: {template_name}")
        
        return self._template_cache[template_name]
    
    def create_inline_prompt(self, template_str: str, context: Dict[str, Any]) -> str:
        """
        Create and render an inline template.
        
        Args:
            template_str: Template string
            context: Variables to inject
            
        Returns:
            Rendered prompt text
        """
        try:
            template = self.env.from_string(template_str)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering inline template: {e}")
            raise LLMError(f"Failed to render inline template: {e}")


# Global prompt manager instance
prompt_manager = PromptManager()
