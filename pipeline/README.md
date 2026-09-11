# Prompt-to-Video Pipeline

Multi-agent explainer-video generator. The site (`/`) is static; this pipeline
runs on Modal and is triggered via Cloudflare Pages Functions (`/functions`).

## Architecture

```
topic
  └─> planner        topic -> learning arc (beats)
  └─> architect      beats -> scenes with narration scripts
  └─> visual         scene -> creative visual brief (parallel)
  └─> tts            narration -> mp3 + word timestamps (parallel, ElevenLabs)
  └─> coder          scene+brief+timestamps -> Remotion TSX (full creative control)
        └─ correctness loop: code must compile & render (<=3 attempts)
  └─> render         Remotion -> mp4 per scene (parallel Modal workers)
  └─> mux + concat   ffmpeg: narration muxed per scene, scenes concatenated
  └─> R2             final mp4 -> public URL
```

**Sync model:** audio is the master clock. Each scene's duration is derived from
its narration mp3; the coder receives word-level timestamps as hard constraints.

**v1 scope:** no taste critic — the coder has full creative control. Only
correctness is enforced (compile + render). A vision critic can be added later
if quality needs it.

**Speed:** scenes fan out across Modal containers; the critic was dropped;
720p drafts optional later. Target: 3-6 min for a ~2 min video.

## Deploy

```bash
cd pipeline
modal secret create ptv-secrets \
  LLM_API_KEY=... \
  LLM_BASE_URL=https://openrouter.ai/api/v1 \
  LLM_MODEL=google/gemini-3.8-flash \
  LLM_MODEL_PLANNER=google/gemini-3.8-flash \
  LLM_MODEL_ARCHITECT=google/gemini-3.8-flash \
  LLM_MODEL_VISUAL=google/gemini-3.8-flash \
  LLM_MODEL_CODER=openai/gpt-5.6-sol \
  R2_ENDPOINT=... R2_KEY_ID=... R2_KEY_SECRET=... \
  R2_BUCKET=... R2_PUBLIC_BASE=... PTV_WEBHOOK_SECRET=...
modal deploy pipeline/modal_app.py
```

TTS runs on the same OpenRouter key via the Kokoro 82M model
(`hexgrad/kokoro-82m`); word timestamps come from a local faster-whisper
pass. Optional overrides: `TTS_MODEL`, `TTS_VOICE` (default `af_bella`).

The LLM client is provider-agnostic (OpenAI-compatible). With OpenRouter a single
`LLM_API_KEY` covers all providers; set per-agent models via
`LLM_MODEL_PLANNER`, `LLM_MODEL_ARCHITECT`, `LLM_MODEL_VISUAL`, `LLM_MODEL_CODER`
(e.g. a cheap fast model for planning, a strong one for the coder).

Then set Pages env vars: `MODAL_GENERATE_URL`, `MODAL_STATUS_URL` (the two
deployed web endpoint URLs), `MODAL_WEBHOOK_SECRET` (same value as
PTV_WEBHOOK_SECRET).

## Layout

- `modal_app.py` — Modal app: webhooks + workers
- `orchestrator.py` — pipeline coordination, render/concat/upload
- `llm.py` — provider-agnostic LLM client (OpenAI-compatible)
- `agents/` — planner, architect, visual, coder
- `tts.py` — ElevenLabs with word timestamps
- `remotion/` — Remotion template baked into the Modal image
