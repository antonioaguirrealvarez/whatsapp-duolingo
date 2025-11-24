"""WhatsApp webhook endpoints for receiving messages and verification."""

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status

from src.core.config import get_settings
from src.core.exceptions import ValidationError, WhatsAppAPIError

logger = logging.getLogger(__name__)
settings = get_settings()

# Create FastAPI router
router = FastAPI()


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify webhook signature from WhatsApp/Twilio.
    
    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.VERIFY_TOKEN:
        # Skip verification if no verify token is configured (for development)
        logger.warning("Webhook verification skipped - no VERIFY_TOKEN configured")
        return True
    
    if not signature:
        logger.error("Missing webhook signature")
        return False
    
    try:
        # Extract signature hash
        signature_hash = signature.replace("sha256=", "")
        
        # Compute expected signature
        expected_signature = hmac.new(
            settings.VERIFY_TOKEN.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        is_valid = hmac.compare_digest(signature_hash, expected_signature)
        
        if not is_valid:
            logger.error("Invalid webhook signature")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


@router.get("/")
async def verify_webhook(request: Request) -> Response:
    """
    Verify webhook endpoint for WhatsApp/Twilio.
    
    This endpoint handles the webhook verification challenge.
    WhatsApp/Twilio will send a GET request with hub.mode, hub.verify_token,
    and hub.challenge parameters to verify the webhook URL.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Response with challenge or error
        
    Raises:
        HTTPException: If verification fails
    """
    try:
        # Get query parameters
        hub_mode = request.query_params.get("hub.mode")
        hub_verify_token = request.query_params.get("hub.verify_token")
        hub_challenge = request.query_params.get("hub.challenge")
        
        logger.info(f"Webhook verification request: mode={hub_mode}, token={hub_verify_token}")
        
        # For Twilio, we might not have these parameters
        if not hub_mode and not hub_verify_token:
            # This might be a Twilio webhook setup
            logger.info("Twilio webhook detected - returning 200 OK")
            return Response(status_code=status.HTTP_200_OK)
        
        # Verify the webhook (WhatsApp Business API style)
        if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
            logger.info("Webhook verification successful")
            return Response(content=hub_challenge, status_code=status.HTTP_200_OK)
        else:
            logger.error(f"Webhook verification failed: mode={hub_mode}, token={hub_verify_token}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webhook verification failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/")
async def receive_message(request: Request) -> Dict[str, Any]:
    """
    Receive incoming WhatsApp messages.
    
    This endpoint handles incoming messages from WhatsApp/Twilio.
    It verifies the signature, logs the message, and returns immediately.
    The actual message processing happens asynchronously.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Success response
        
    Raises:
        HTTPException: If message processing fails
    """
    try:
        # Get raw request body
        body = await request.body()
        
        # Get signature header
        signature = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Twilio-Signature")
        
        # Verify signature (if configured)
        if not verify_webhook_signature(body, signature or ""):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature"
            )
        
        # Parse JSON payload
        try:
            payload = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Log the incoming message
        logger.info(f"Received WhatsApp message: {payload}")
        
        # TODO: Process message asynchronously
        # For now, just acknowledge receipt
        # In future phases, this will trigger the orchestrator
        
        # Trigger orchestrator for message processing
        from src.orchestrator.core import orchestrator
        
        # Process asynchronously (fire and forget)
        import asyncio
        asyncio.create_task(orchestrator.process_event(payload))
        
        # Return immediately (asynchronous processing pattern)
        return {"status": "received", "message": "Message processing started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
