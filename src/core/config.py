"""Core configuration settings for WhatsApp-Duolingo application."""

import logging
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="Default OpenAI model")
    
    # LangSmith Configuration (Optional)
    LANGSMITH_TRACING: bool = Field(default=False, description="Enable LangSmith tracing")
    LANGSMITH_ENDPOINT: str = Field(default="https://api.smith.langchain.com", description="LangSmith endpoint")
    LANGSMITH_API_KEY: Optional[str] = Field(default=None, description="LangSmith API key")
    LANGSMITH_PROJECT: str = Field(default="whatsapp-duolingo", description="LangSmith project name")
    
    # Twilio Configuration (WhatsApp)
    TWILIO_ACCOUNT_SID: str = Field(..., description="Twilio Account SID")
    TWILIO_AUTH_TOKEN: str = Field(..., description="Twilio Auth Token")
    TWILIO_WHATSAPP_NUMBER: str = Field(..., description="Twilio WhatsApp number")
    YOUR_WHATSAPP_NUMBER: str = Field(..., description="Your personal WhatsApp number for testing")
    TWILIO_TEMPLATE_CARD_SID: Optional[str] = Field(default=None, description="Twilio template card SID")
    TWILIO_TEMPLATE_LIST_SID: Optional[str] = Field(default=None, description="Twilio template list SID")
    
    # WhatsApp Business API Configuration (Scaffold for future migration)
    WHATSAPP_TOKEN: Optional[str] = Field(default=None, description="WhatsApp Business API token")
    VERIFY_TOKEN: Optional[str] = Field(default=None, description="Webhook verification token")
    PHONE_NUMBER_ID: Optional[str] = Field(default=None, description="WhatsApp phone number ID")
    
    # External APIs
    FIRECRAWL_API_KEY: str = Field(..., description="Firecrawl API key for web search")
    
    # Application Configuration
    APP_NAME: str = Field(default="WhatsApp-Duolingo", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    
    # Redis Configuration (for session management)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # Database Configuration (for future use)
    DATABASE_URL: Optional[str] = Field(default="sqlite:///./whatsapp_duolingo.db", description="Database connection URL")
    
    @property
    def twilio_client_params(self) -> dict:
        """Get Twilio client initialization parameters."""
        return {
            "account_sid": self.TWILIO_ACCOUNT_SID,
            "auth_token": self.TWILIO_AUTH_TOKEN,
        }
    
    @property
    def openai_client_params(self) -> dict:
        """Get OpenAI client initialization parameters."""
        return {
            "api_key": self.OPENAI_API_KEY,
            "model": self.OPENAI_MODEL,
        }
    
    @property
    def langsmith_config(self) -> dict:
        """Get LangSmith configuration if enabled."""
        if not self.LANGSMITH_TRACING or not self.LANGSMITH_API_KEY:
            return {}
        return {
            "tracing": self.LANGSMITH_TRACING,
            "endpoint": self.LANGSMITH_ENDPOINT,
            "api_key": self.LANGSMITH_API_KEY,
            "project": self.LANGSMITH_PROJECT,
        }
    
    def setup_logging(self) -> None:
        """Configure logging based on settings."""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the application settings instance."""
    return settings
