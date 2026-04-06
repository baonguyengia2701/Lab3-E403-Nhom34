"""
provider.py — LLMProvider interface cho Lab 3.

Mục tiêu Objective 3: Provider Switching
  Swap between OpenAI and Gemini seamlessly using the LLMProvider interface.

Cách dùng:
    from provider import build_provider

    provider = build_provider()           # đọc từ .env
    provider = build_provider("gemini")   # chỉ định cụ thể
    provider = build_provider("openai", model="gpt-4o-mini")

    content, usage = provider.chat(messages)
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# BASE INTERFACE
# =============================================================================

class LLMProvider:
    """
    Abstract interface cho tất cả LLM providers.
    Mỗi subclass phải implement chat().
    """

    name: str = "base"
    model: str = ""

    def chat(self, messages: list, **kwargs) -> tuple:
        """
        Gọi LLM với danh sách messages.

        Args:
            messages: List[{"role": str, "content": str}]
            **kwargs: Các tham số bổ sung (temperature, max_tokens, ...)

        Returns:
            (content: str, usage: dict)
            usage = {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
        """
        raise NotImplementedError("Subclasses must implement chat()")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"


# =============================================================================
# OPENAI PROVIDER
# =============================================================================

class OpenAIProvider(LLMProvider):
    """
    Provider dùng OpenAI API (GPT-3.5, GPT-4o, GPT-4o-mini...).
    """

    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from openai import OpenAI
        self.model = model or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def chat(self, messages: list, **kwargs) -> tuple:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        content = response.choices[0].message.content.strip()
        usage = {
            "prompt_tokens":     response.usage.prompt_tokens     if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens":      response.usage.total_tokens      if response.usage else 0,
        }
        return content, usage


# =============================================================================
# GEMINI PROVIDER  (dùng OpenAI-compatible endpoint của Google)
# =============================================================================

class GeminiProvider(LLMProvider):
    """
    Provider dùng Google Gemini qua OpenAI-compatible endpoint.
    Không cần cài thêm SDK — dùng openai package như OpenAIProvider.

    Các model phổ biến:
        gemini-2.0-flash  (nhanh, rẻ — khuyến nghị)
        gemini-1.5-flash
        gemini-1.5-pro
    """

    name = "gemini"
    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from openai import OpenAI
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.client = OpenAI(
            api_key=api_key or os.getenv("GEMINI_API_KEY"),
            base_url=self._BASE_URL,
        )

    def chat(self, messages: list, **kwargs) -> tuple:
        # Gemini không hỗ trợ một số kwargs của OpenAI — lọc bỏ nếu cần
        kwargs.pop("logprobs", None)
        kwargs.pop("top_logprobs", None)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        content = response.choices[0].message.content.strip()
        usage = {
            "prompt_tokens":     response.usage.prompt_tokens     if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens":      response.usage.total_tokens      if response.usage else 0,
        }
        return content, usage


# =============================================================================
# FACTORY
# =============================================================================

def build_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMProvider:
    """
    Factory — Tạo provider từ tên.

    Args:
        provider_name: 'openai' | 'gemini'
                       (mặc định: đọc từ DEFAULT_PROVIDER env, fallback 'openai')
        model:         Tên model cụ thể (mặc định: từ DEFAULT_MODEL / GEMINI_MODEL env)
        api_key:       API key (mặc định: từ OPENAI_API_KEY / GEMINI_API_KEY env)

    Returns:
        OpenAIProvider hoặc GeminiProvider
    """
    name = (provider_name or os.getenv("DEFAULT_PROVIDER", "openai")).lower().strip()

    if name == "gemini":
        return GeminiProvider(api_key=api_key, model=model)
    elif name == "openai":
        return OpenAIProvider(api_key=api_key, model=model)
    else:
        raise ValueError(
            f"Provider '{name}' không được hỗ trợ. Chọn: 'openai' | 'gemini'"
        )


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Provider Switching Test")
    print("=" * 60)

    for pname in ["openai", "gemini"]:
        print(f"\n[{pname.upper()}]")
        try:
            p = build_provider(pname)
            content, usage = p.chat([
                {"role": "user", "content": "Chào! Bạn là model gì? Trả lời 1 câu ngắn."},
            ])
            print(f"  Model  : {p.model}")
            print(f"  Answer : {content[:120]}")
            print(f"  Tokens : {usage['total_tokens']}")
        except Exception as e:
            print(f"  ERROR  : {e}")
