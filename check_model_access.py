"""Probe which Claude models this API key can actually reach.

Sends one tiny real request per model. Use it to confirm a model is available
and billable BEFORE pointing LLM_MODEL at it in .env and paying for a full
8-agent briefing run.

    py -3.12 check_model_access.py                 # probe sonnet + fable
    py -3.12 check_model_access.py claude-opus-5   # probe specific model(s)

Note on the Anthropic console: the Usage dashboard shows 0 for a model you have
never called — that is expected and says nothing about whether you can call it.
Credit *balance* is what gates access, and it is account-wide, not per-model:
if this script reports "credit balance is too low" for every model, no amount of
per-model credit will help until the balance on THIS key's workspace is topped
up. Check Plans & Billing, and confirm the key belongs to the workspace holding
the credits.
"""

import sys

from config.settings import (
    ANTHROPIC_API_KEY,
    LLM_MODEL,
    LLM_MODEL_FABLE,
    LLM_MODEL_SONNET,
    model_always_thinks,
    model_rejects_temperature,
)


def probe(client, model: str) -> bool:
    """Send one minimal request, honouring the model's parameter constraints."""
    kwargs = {
        # Always-thinking models spend tokens reasoning before any visible text,
        # so a 1-token probe would truncate before producing an answer.
        "max_tokens": 1024 if model_always_thinks(model) else 16,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
    }
    # temperature is rejected outright (HTTP 400) by the newer model families.
    if not model_rejects_temperature(model):
        kwargs["temperature"] = 0.0

    try:
        r = client.messages.create(model=model, **kwargs)
    except Exception as e:
        print(f"  [FAIL] {model}")
        print(f"         {type(e).__name__}: {str(e)[:300]}")
        return False

    text = "".join(b.text for b in r.content if b.type == "text").strip()
    print(f"  [OK]   {model}")
    print(
        f"         served={r.model} stop={r.stop_reason} "
        f"in={r.usage.input_tokens} out={r.usage.output_tokens} reply={text!r}"
    )
    return True


def main() -> int:
    if not ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY not set in .env — nothing to probe.")
        return 1

    import anthropic

    models = sys.argv[1:] or [LLM_MODEL_SONNET, LLM_MODEL_FABLE]
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print(f"Key: {ANTHROPIC_API_KEY[:18]}...{ANTHROPIC_API_KEY[-4:]}")
    print(f"Active LLM_MODEL in .env: {LLM_MODEL}\n")
    print("Probing:")

    reachable = [m for m in models if probe(client, m)]

    print()
    if not reachable:
        print("No model reachable. If the error says 'credit balance is too low',")
        print("that is account-wide - top up Plans & Billing, and verify this key")
        print("belongs to the workspace that holds your credits.")
        return 1

    print(f"Reachable: {', '.join(reachable)}")
    print("Point LLM_MODEL in .env at whichever you want the agents to use.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
