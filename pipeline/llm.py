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


def chat(system, user, json_mode=True, model=None, max_tokens=4000, temperature=0.7,
         web_search=False):
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
    if web_search:
        # OpenRouter web plugin with no engine -> the provider's NATIVE search.
        # For Google models that's Gemini's built-in Google Search grounding
        # (billed as provider passthrough on the same OpenRouter key).
        payload["plugins"] = [{"id": "web"}]
    resp = _post(base, api_key, payload)
    if resp is None:
        # Web grounding is best-effort: the search plugin can transiently fail
        # (HTTP 400s seen 2026-09-13). Retry once as a plain chat call so one
        # flaky plugin never fails the whole video.
        del payload["plugins"]
        resp = _post(base, api_key, payload)
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content) if json_mode else content


def _post(base, api_key, payload):
    """POST a chat payload. Returns None (instead of raising) when the
    web-search plugin was attached and the call failed, so the caller can
    retry without it. All other errors raise with the API's error body."""
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=300,
    )
    if resp.status_code >= 400:
        # Include the API's error body — raise_for_status() drops it, which
        # makes 400s undebuggable from the stored job record.
        err = RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text[:1500]}")
        if payload.get("plugins"):
            return None
        raise err
    return resp
