"""Text-to-speech via OpenRouter (Kokoro 82M), with word-level timestamps.

Uses OpenRouter's OpenAI-compatible /audio/speech endpoint with the
hexgrad/kokoro-82m model — the same API key as the LLM agents, so no
separate TTS provider is needed. Kokoro returns raw audio but no
timestamps, so word timings come from a local faster-whisper pass (CPU)
aligned against the known narration text.

Env:
  LLM_API_KEY  (required; OpenRouter key)
  LLM_BASE_URL (default https://openrouter.ai/api/v1)
  TTS_MODEL    (default hexgrad/kokoro-82m)
  TTS_VOICE    (default af_bella)

synthesize(text) -> {"mp3_path": ..., "duration_sec": ..., "words": [{"word","start","end"}]}
"""
import difflib
import os
import re
import subprocess
import tempfile
import threading

import requests

_WHISPER_MODEL = None
_WHISPER_LOCK = threading.Lock()


def _base_url():
    return os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")


def synthesize(text, out_path=None):
    api_key = os.environ["LLM_API_KEY"]
    model = os.environ.get("TTS_MODEL", "hexgrad/kokoro-82m")
    voice = os.environ.get("TTS_VOICE", "af_bella")
    out_path = out_path or tempfile.mktemp(suffix=".mp3")

    resp = requests.post(
        f"{_base_url()}/audio/speech",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://prompt-to-video-eso.pages.dev",
            "X-Title": "prompt-to-video",
        },
        json={
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
        },
        timeout=300,
    )
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)

    duration = _mp3_duration(out_path)
    words = _word_timestamps(out_path, text, duration)
    return {"mp3_path": out_path, "duration_sec": duration, "words": words}


def _mp3_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel

        _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_MODEL


def _norm(w):
    return re.sub(r"[^\w']", "", w.lower())


def _word_timestamps(mp3_path, text, duration):
    """Word timings via faster-whisper, aligned to the narration text."""
    true_words = text.split()
    if not true_words or duration <= 0:
        return []

    try:
        with _WHISPER_LOCK:
            segments, _ = _whisper_model().transcribe(
                mp3_path, word_timestamps=True, beam_size=1
            )
            heard = [
                (w.word.strip(), w.start, w.end)
                for s in segments
                for w in (s.words or [])
                if w.word.strip()
            ]
    except Exception:
        heard = []

    if not heard:
        return _proportional(true_words, duration)

    heard_norm = [_norm(w) for w, _, _ in heard]
    true_norm = [_norm(w) for w in true_words]
    sm = difflib.SequenceMatcher(None, heard_norm, true_norm, autojunk=False)

    # For each true word, collect candidate timings from matched heard words.
    timed = [None] * len(true_words)
    for h0, t0, size in sm.get_matching_blocks():
        for k in range(size):
            hw, hs, he = heard[h0 + k]
            timed[t0 + k] = (hs, he)

    # Fill gaps by interpolating between anchored neighbors.
    return _interpolate(true_words, timed, duration)


def _interpolate(true_words, timed, duration):
    n = len(true_words)
    # Anchor list: (index, start, end) for timed words, plus virtual endpoints.
    anchors = [(i, s, e) for i, t in enumerate(timed) if t is not None
               for s, e in [t]]
    if not anchors:
        return _proportional(true_words, duration)
    anchors = [(-1, 0.0, 0.0)] + anchors + [(n, duration, duration)]

    out = []
    for i, w in enumerate(true_words):
        if timed[i] is not None:
            s, e = timed[i]
        else:
            # Find surrounding anchors and interpolate by character weight.
            prev = max(a for a in anchors if a[0] < i)
            nxt = min(a for a in anchors if a[0] > i)
            span_chars = sum(len(true_words[j]) for j in range(prev[0] + 1, nxt[0]))
            if span_chars <= 0:
                s = e = (prev[2] + nxt[1]) / 2
            else:
                t0 = prev[2]
                t1 = nxt[1]
                before = sum(len(true_words[j]) for j in range(prev[0] + 1, i))
                frac0 = before / span_chars
                frac1 = (before + len(w)) / span_chars
                s = t0 + frac0 * (t1 - t0)
                e = t0 + frac1 * (t1 - t0)
        out.append({"word": w, "start": round(s, 3), "end": round(e, 3)})
    return out


def _proportional(true_words, duration):
    total = sum(len(w) for w in true_words) or 1
    out, t = [], 0.0
    for w in true_words:
        e = t + duration * len(w) / total
        out.append({"word": w, "start": round(t, 3), "end": round(e, 3)})
        t = e
    return out
