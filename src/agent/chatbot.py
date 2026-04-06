import os
from typing import Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class SimpleChatbot:
    """
    Baseline chatbot that calls the LLM directly without any tools or reasoning loop.
    Used to demonstrate the limitations of a plain LLM on multi-step tasks.
    """

    def __init__(self, llm: LLMProvider, system_prompt: Optional[str] = None):
        self.llm = llm
        self.system_prompt = system_prompt or (
            "You are a helpful assistant. Answer the user's question as accurately as possible."
        )
        self.history = []

    def chat(self, user_input: str) -> str:
        """
        Send a message to the LLM and return the response text.
        Logs the event and tracks performance metrics.
        """
        logger.log_event("CHATBOT_START", {
            "input": user_input,
            "model": self.llm.model_name
        })

        try:
            result = self.llm.generate(user_input, system_prompt=self.system_prompt)

            content = result["content"]
            usage = result.get("usage", {})
            latency_ms = result.get("latency_ms", 0)
            provider = result.get("provider", "unknown")

            tracker.track_request(
                provider=provider,
                model=self.llm.model_name,
                usage=usage,
                latency_ms=latency_ms,
            )

            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": content})

            logger.log_event("CHATBOT_RESPONSE", {
                "input": user_input,
                "output": content,
                "latency_ms": latency_ms,
                "tokens": usage.get("total_tokens", 0),
            })

            return content

        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return f"Error: {str(e)}"
