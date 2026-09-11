"""Shared LLM client. Provider-agnostic via an OpenAI-compatible endpoint.

Env:
  LLM_API_KEY   (required)
  LLM_BASE_URL  (default https://api.openai.com/v1)
  LLM_MODEL     (default gpt-4o)
"""
import json
import os

import requests


def model_for(role):
    """Per-agent model override, e.g. LLM_MODEL_CODER, else LLM_MODEL.

    With OpenRouter (LLM_BASE_URL=https://openrouter.ai/api/v1) this lets each
    agent run on a different provider/model with a single API key, e.g.
    LLM_MODEL_CODER=anthropic/claude-sonnet-4.5 and
    LLM_MODEL_PLANNER=google/gemini-2.5-flash.
    """
    return os.environ.get(
        f"LLM_MODEL_{role.upper()}", os.environ.get("LLM_MODEL", "gpt-4o")
    )


def chat(system, user, json_mode=True, model=None, max_tokens=4000, temperature=0.7):
    api_key = os.environ["LLM_API_KEY"]
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = model or os.environ.get("LLM_MODEL", "gpt-4o")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=300,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content) if json_mode else content
