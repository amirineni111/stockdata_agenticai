"""Single construction point for the CrewAI LLM used by every agent.

Why this exists: the platform needs to run on two model generations with
incompatible request surfaces.

    claude-sonnet-4-6  accepts `temperature`, no extended thinking
    claude-fable-5     rejects `temperature` (HTTP 400), thinking always on

Rather than teach nine agent factories about that difference, they all call
`build_llm()` and state their *intent* (a temperature they'd like, a token
budget they need). This module drops or adjusts those parameters to match
whatever LLM_MODEL is active, so switching models is a one-line .env change.

CrewAI routes `anthropic/<model>` to its native Anthropic provider, which only
forwards `temperature` when it is not None — so omitting it here is enough to
keep the request legal on the newer models.

Deliberately NOT imported by config/settings.py: the standalone report scripts
(ml_bucket_report, forex_tomorrow_report, weekly_screening_report, ...) import
settings for SQL/SMTP config only and must not pay to import CrewAI.
"""

from __future__ import annotations

from config.settings import (
    LLM_MODEL,
    model_rejects_temperature,
    resolve_max_tokens,
)


def build_llm(max_tokens: int, temperature: float | None = None, model: str | None = None):
    """Build a CrewAI LLM for the active model, adapting incompatible params.

    Args:
        max_tokens: Token budget the agent wants for its answer. Raised to the
            thinking floor automatically on always-thinking models.
        temperature: Desired sampling temperature. Silently dropped on models
            that reject it — those are steered by prompt wording instead.
        model: Override the active LLM_MODEL (used by probes/tests).

    Returns:
        crewai.LLM configured for the resolved model.
    """
    from crewai import LLM  # imported lazily — keeps SQL/SMTP-only scripts light

    resolved = model or LLM_MODEL
    kwargs = {
        "model": f"anthropic/{resolved}",
        "max_tokens": resolve_max_tokens(max_tokens, resolved),
    }
    if temperature is not None and not model_rejects_temperature(resolved):
        kwargs["temperature"] = temperature

    return LLM(**kwargs)


def describe_active_model(model: str | None = None) -> str:
    """One-line summary of how the active model will be called (for logs/preflight)."""
    from config.settings import model_always_thinks

    resolved = model or LLM_MODEL
    bits = [resolved]
    bits.append("temperature=dropped" if model_rejects_temperature(resolved) else "temperature=sent")
    if model_always_thinks(resolved):
        bits.append(f"thinking=always-on (max_tokens floor {resolve_max_tokens(1, resolved)})")
    else:
        bits.append("thinking=off")
    return " | ".join(bits)
