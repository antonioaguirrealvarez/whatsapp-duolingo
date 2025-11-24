"""Custom exceptions for WhatsApp-Duolingo application."""


class WhatsAppDuolingoError(Exception):
    """Base exception for all WhatsApp-Duolingo errors."""
    pass


class ConfigurationError(WhatsAppDuolingoError):
    """Raised when configuration is invalid or missing."""
    pass


class WhatsAppAPIError(WhatsAppDuolingoError):
    """Raised when WhatsApp API operations fail."""
    pass


class TwilioError(WhatsAppAPIError):
    """Raised when Twilio API operations fail."""
    pass


class LLMError(WhatsAppDuolingoError):
    """Raised when LLM operations fail."""
    pass


class OpenAIError(LLMError):
    """Raised when OpenAI API operations fail."""
    pass


class OrchestratorError(WhatsAppDuolingoError):
    """Raised when orchestrator operations fail."""
    pass


class SessionError(WhatsAppDuolingoError):
    """Raised when session management operations fail."""
    pass


class UserNotFoundError(WhatsAppDuolingoError):
    """Raised when a user is not found in the system."""
    pass


class ValidationError(WhatsAppDuolingoError):
    """Raised when input validation fails."""
    pass


class RateLimitError(WhatsAppDuolingoError):
    """Raised when rate limits are exceeded."""
    pass


class PaymentError(WhatsAppDuolingoError):
    """Raised when payment operations fail."""
    pass


class ContentGenerationError(WhatsAppDuolingoError):
    """Raised when content generation fails."""
    pass


class EvaluationError(WhatsAppDuolingoError):
    """Raised when answer evaluation fails."""
    pass
