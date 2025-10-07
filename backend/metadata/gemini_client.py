"""
Gemini API client wrapper for metadata generation
"""
import google.generativeai as genai
import time
import config
from utils.logger import setup_logger

class GeminiClient:
    """Wrapper for Gemini API to match LangChain interface."""

    def __init__(self):
        """Initialize Gemini client."""
        self.logger = setup_logger("GeminiClient")

        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        # Configure Gemini
        genai.configure(api_key=config.GEMINI_API_KEY)

        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config={
                "temperature": config.TEMPERATURE,
                "top_p": 0.95,
                "max_output_tokens": 8192,
            }
        )

        self.logger.info(f"Gemini client initialized with model: {config.GEMINI_MODEL}")

    def invoke(self, messages):
        """
        Invoke Gemini API with messages (matching LangChain interface).

        Args:
            messages: List of message dicts or a single message string

        Returns:
            Response object with .content attribute
        """
        # Convert messages to prompt
        if isinstance(messages, list):
            # Extract content from message objects
            prompt_parts = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    prompt_parts.append(msg.content)
                elif isinstance(msg, dict):
                    prompt_parts.append(msg.get('content', str(msg)))
                else:
                    prompt_parts.append(str(msg))
            prompt = "\n".join(prompt_parts)
        else:
            prompt = str(messages)

        # Call Gemini API with retry logic
        max_retries = config.RETRY_LIMIT
        retry_delay = config.RETRY_DELAY

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)

                # Check if response was blocked
                if not response.text:
                    self.logger.warning("Response was blocked or empty")
                    return GeminiResponse("")

                return GeminiResponse(response.text)

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All retry attempts failed")
                    raise

class GeminiResponse:
    """Wrapper for Gemini response to match LangChain interface."""

    def __init__(self, content):
        self.content = content

    def __str__(self):
        return self.content
