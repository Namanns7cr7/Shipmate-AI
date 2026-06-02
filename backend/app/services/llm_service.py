"""
LLM Service — Optional enhancement layer.

In the MVP, agents use deterministic rule-based analysis.
This service provides an integration point for adding LLM reasoning
(Azure OpenAI, Anthropic, etc.) when available.

To enable: set AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY in .env
"""

import os
from typing import Optional


class LLMService:
    _enabled: Optional[bool] = None

    @classmethod
    def is_available(cls) -> bool:
        if cls._enabled is None:
            cls._enabled = bool(
                os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY")
            ) or bool(os.getenv("OPENAI_API_KEY")) or bool(os.getenv("ANTHROPIC_API_KEY"))
        return cls._enabled

    @classmethod
    async def enhance_analysis(cls, agent_name: str, context: dict, base_output: dict) -> dict:
        """
        Optionally enhance a rule-based agent output with LLM reasoning.
        Falls back gracefully to base_output if LLM is unavailable.
        """
        if not cls.is_available():
            return base_output

        # Future: call Azure OpenAI / Anthropic here
        # prompt = build_prompt(agent_name, context, base_output)
        # response = await call_llm(prompt)
        # return merge(base_output, parse(response))

        return base_output
