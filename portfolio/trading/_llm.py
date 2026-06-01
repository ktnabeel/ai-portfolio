"""Shared LLM factory — creates provider-specific ChatModel instances.

All Trading agents use this factory so a single UI dropdown controls
the provider and model for every agent in the pipeline.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.language_models import BaseChatModel

ProviderName = Literal["openai", "anthropic", "nvidia"]
"""Supported LLM providers."""

# Model lists per provider — curated for the trading use case.
# Models are ordered: best for reasoning first.
_OPENAI_MODELS: dict[str, str] = {
    "gpt-4o": "GPT-4o — best overall reasoning",
    "gpt-4o-mini": "GPT-4o Mini — fast, cost-effective",
    "gpt-4.1": "GPT-4.1 — latest flagship",
    "o3-mini": "o3-mini — reasoning specialist",
}
_ANTHROPIC_MODELS: dict[str, str] = {
    "claude-sonnet-4-20250514": "Claude Sonnet 4 — balanced speed + quality",
    "claude-3-5-sonnet-latest": "Claude 3.5 Sonnet — reliable all-rounder",
    "claude-3-5-haiku-latest": "Claude 3.5 Haiku — fast, lightweight",
    "claude-opus-4-20250514": "Claude Opus 4 — best reasoning (slower)",
}
_NVIDIA_MODELS: dict[str, str] = {
    "nvidia/llama-3.1-nemotron-70b-instruct": "Llama 3.1 Nemotron 70B — balanced reasoning",
    "meta/llama-3.1-70b-instruct": "Llama 3.1 70B Instruct — strong general analysis",
    "meta/llama-3.1-8b-instruct": "Llama 3.1 8B Instruct — lower-latency option",
}

PROVIDER_MODELS: dict[str, dict[str, str]] = {
    "openai": _OPENAI_MODELS,
    "anthropic": _ANTHROPIC_MODELS,
    "nvidia": _NVIDIA_MODELS,
}
"""Provider → {model_id: description} mapping for UI dropdowns."""


def get_default_model(provider: str) -> str:
    """Return the recommended default model for a provider."""
    defaults: dict[str, str] = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
        "nvidia": "nvidia/llama-3.1-nemotron-70b-instruct",
    }
    return defaults.get(provider, "gpt-4o")


def create_llm(
    provider: ProviderName = "openai",
    model: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.3,
) -> BaseChatModel:
    """Create a LangChain ChatModel for the given provider.

    Args:
        provider: ``"openai"``, ``"anthropic"``, or ``"nvidia"``.
        model: Model name (e.g. ``"gpt-4o"``, ``"claude-sonnet-4-20250514"``).
               Defaults to the recommended model for the provider.
        api_key: API key for the provider. If empty/None, falls back to
                 the standard environment variable (``OPENAI_API_KEY``
                 ``ANTHROPIC_API_KEY``, or ``NVIDIA_API_KEY``).
        temperature: Sampling temperature (default 0.3).

    Returns:
        A configured ``BaseChatModel`` instance.

    Raises:
        ValueError: If *provider* is not supported.
    """
    model = model or get_default_model(provider)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict = {"model": model, "temperature": temperature}
        if api_key:
            kwargs["openai_api_key"] = api_key
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {"model": model, "temperature": temperature}
        if api_key:
            kwargs["anthropic_api_key"] = api_key
        return ChatAnthropic(**kwargs)

    if provider == "nvidia":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": model,
            "temperature": temperature,
            "base_url": "https://integrate.api.nvidia.com/v1",
        }
        if api_key:
            kwargs["openai_api_key"] = api_key
        return ChatOpenAI(**kwargs)

    raise ValueError(
        f"Unsupported LLM provider: {provider!r}. Choose 'openai', 'anthropic', or 'nvidia'."
    )
