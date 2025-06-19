import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class AIError(Exception):
    """Base exception for AI service errors."""
    pass

class AITimeoutError(AIError):
    """Exception raised when AI request times out."""
    pass

class AIRateLimitError(AIError):
    """Exception raised when AI rate limit is exceeded."""
    pass

class AIServiceError(AIError):
    """Exception raised for general AI service errors."""
    pass

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Available models and their configurations
AVAILABLE_MODELS = {
    "gpt-4": {
        "id": "openai/gpt-4",
        "max_tokens": 4096,
        "temperature": 0.7,
        "description": "Most capable model, best for complex interpretations"
    },
    "gpt-3.5-turbo": {
        "id": "openai/gpt-3.5-turbo",
        "max_tokens": 2048,
        "temperature": 0.7,
        "description": "Fast and efficient, good for basic interpretations"
    },
    "claude-3-opus": {
        "id": "anthropic/claude-3-opus",
        "max_tokens": 4096,
        "temperature": 0.7,
        "description": "Strong analytical capabilities, good for detailed interpretations"
    },
    "claude-3-sonnet": {
        "id": "anthropic/claude-3-sonnet",
        "max_tokens": 4096,
        "temperature": 0.7,
        "description": "Balanced performance, good for general interpretations"
    },
    "mistral-medium": {
        "id": "mistralai/mistral-medium",
        "max_tokens": 2048,
        "temperature": 0.7,
        "description": "Open source model with good balance of speed and accuracy"
    },
    "mistral-7b": {
        "id": "mistralai/mistral-7b-instruct",
        "max_tokens": 2048,
        "temperature": 0.7,
        "description": "Fast and efficient open source model"
    }
}

DEFAULT_MODEL = "gpt-4"
TIMEOUT = 30  # seconds

def validate_api_key() -> None:
    """
    Validate that the OpenRouter API key is set.
    
    Raises:
        ValueError: If API key is not set
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")

def get_available_models() -> list:
    """Get list of available AI models."""
    return ['gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'claude-3-sonnet', 'mistral-medium', 'mistral-7b']

def validate_model(model_name: str) -> None:
    """
    Validate that the requested model is available.
    
    Args:
        model_name: Name of the model to validate
    
    Raises:
        ValueError: If model is not available
    """
    if model_name not in AVAILABLE_MODELS:
        available = ", ".join(AVAILABLE_MODELS.keys())
        raise ValueError(f"Invalid model: {model_name}. Available models: {available}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((AITimeoutError, AIServiceError))
)
def generate_interpretation(
    prompt: str,
    model_name: str = 'gpt-4',
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: int = 30
) -> str:
    """
    Generate interpretation using OpenRouter API with retry logic.
    
    Args:
        prompt: The prompt to send to the AI
        model_name: The AI model to use
        temperature: Controls randomness (0.0 to 1.0)
        max_tokens: Maximum length of response
        timeout: Request timeout in seconds
        
    Returns:
        Generated interpretation text
        
    Raises:
        AITimeoutError: If request times out
        AIRateLimitError: If rate limit is exceeded
        AIServiceError: For other AI service errors
    """
    try:
        # Get API key from environment
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise AIServiceError("OpenRouter API key not found in environment variables")

        # Prepare request
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://outer-skies.com',  # Replace with your domain
            'X-Title': 'Outer Skies Astrology'  # Replace with your app name
        }
        
        # Get the correct model ID from AVAILABLE_MODELS
        if model_name in AVAILABLE_MODELS:
            model_id = AVAILABLE_MODELS[model_name]["id"]
        else:
            model_id = model_name  # Fallback to using the name directly
        
        data = {
            'model': model_id,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        # Make request with timeout
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=timeout
        )
        
        # Handle different response status codes
        if response.status_code == 429:
            raise AIRateLimitError("AI service rate limit exceeded")
        elif response.status_code == 408:
            raise AITimeoutError("AI service request timed out")
        elif response.status_code != 200:
            raise AIServiceError(f"AI service error: {response.status_code} - {response.text}")
            
        # Parse response
        result = response.json()
        if 'choices' not in result or not result['choices']:
            raise AIServiceError("Invalid response from AI service")
            
        return result['choices'][0]['message']['content'].strip()
        
    except requests.exceptions.Timeout:
        logger.error("AI request timed out")
        raise AITimeoutError("Request to AI service timed out")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"AI request failed: {str(e)}")
        raise AIServiceError(f"Failed to communicate with AI service: {str(e)}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {str(e)}")
        raise AIServiceError("Invalid response from AI service")
        
    except Exception as e:
        logger.error(f"Unexpected error in AI service: {str(e)}")
        raise AIServiceError(f"Unexpected error: {str(e)}")

def fallback_to_alternative_model(
    prompt: str,
    primary_model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """
    Try alternative models if primary model fails.
    
    Args:
        prompt: The prompt to send
        primary_model: The preferred model
        temperature: Controls randomness
        max_tokens: Maximum response length
        
    Returns:
        Generated interpretation from any available model
    """
    available_models = get_available_models()
    if primary_model in available_models:
        available_models.remove(primary_model)
    
    # Try primary model first
    try:
        return generate_interpretation(
            prompt,
            model_name=primary_model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    except AIError as e:
        logger.warning(f"Primary model {primary_model} failed: {str(e)}")
    
    # Try alternative models
    for model in available_models:
        try:
            return generate_interpretation(
                prompt,
                model_name=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except AIError as e:
            logger.warning(f"Alternative model {model} failed: {str(e)}")
            continue
    
    # If all models fail
    raise AIServiceError("All AI models failed to generate interpretation")
