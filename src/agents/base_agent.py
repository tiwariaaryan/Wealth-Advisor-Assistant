import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from google import genai
from google.genai import types
from src.config import config
from src.utils.logger import logger, execution_trace

class BaseAgent(ABC):
    """
    Abstract Base Class for all autonomous agents in the Wealth Advisor system.
    Encapsulates LLM invocation, structured schema enforcement, logging, and error handling.
    """
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.client: Optional[genai.Client] = None
        self._init_llm_client()

    def _init_llm_client(self):
        api_key = config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if api_key and api_key != "your_gemini_api_key_here":
            try:
                self.client = genai.Client(api_key=api_key)
                logger.info(f"Agent '{self.name}': Gemini LLM client initialized successfully.")
            except Exception as e:
                logger.warning(f"Agent '{self.name}': Could not initialize Gemini client: {e}")
                self.client = None
        else:
            self.client = None

    def call_gemini_structured(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        system_instruction: Optional[str] = None
    ) -> BaseModel:
        """
        Calls Gemini with strict Pydantic structured output enforcement.
        Falls back to a rule-based deterministic response if API key is absent or on network error.
        """
        if not self.client:
            self._init_llm_client()

        if self.client:
            try:
                execution_trace.add_event(
                    agent=self.name,
                    action="Invoking Gemini LLM with Structured Schema",
                    details={"model": config.GEMINI_MODEL, "schema": response_schema.__name__}
                )

                gen_config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.2,
                )
                if system_instruction:
                    gen_config.system_instruction = system_instruction

                response = self.client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=prompt,
                    config=gen_config
                )

                # Parse JSON string into Pydantic model
                structured_obj = response_schema.model_validate_json(response.text)
                execution_trace.add_event(
                    agent=self.name,
                    action="Gemini Structured Output Received",
                    status="SUCCESS"
                )
                return structured_obj

            except Exception as e:
                logger.error(f"Agent '{self.name}': Gemini API call failed: {e}. Falling back to rule-based generation.")
                execution_trace.add_event(
                    agent=self.name,
                    action="Gemini LLM Call Failed - Fallback Activated",
                    details=str(e),
                    status="WARNING"
                )

        # Fallback generator if LLM unavailable
        return self._generate_fallback(prompt, response_schema)

    @abstractmethod
    def _generate_fallback(self, prompt: str, schema: Type[BaseModel]) -> BaseModel:
        """Fallback method to produce structured output when LLM is unavailable."""
        pass
