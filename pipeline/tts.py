"""Text-to-speech via ElevenLabs, with word-level timestamps.

Env:
  ELEVENLABS_API_KEY (required)
  ELEVENLABS_VOICE_ID (default: a clear narrator voice)

synthesize(text) -> {"mp3_path": ..., "duration_sec": ..., "words": [{"word","start","end"}]}
"""
import os
import subprocess
import tempfile

import requests

BASE = "https://api.elevenlabs.io/v1"


def synthesize(text, out_path=None):
    api_key = os.environ["ELEVENLABS_API_KEY"]
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    out_path = out_path or tempfile.mktemp(suffix=".mp3")
    resp = requests.post(
        f"{BASE}/text-to-speech/{voice_id}/with-timestamps",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    audio_b64 = data["audio_base64"]
    import base64

    with open(out_path, "wb") as f:
        f.write(base64.b64decode(audio_b64))

    words = [
        {"word": w, "start": s, "end": e}
        for w, s, e in zip(
            data["alignment"]["characters"],
            data["alignment"]["character_start_times_seconds"],
            data["alignment"]["character_end_times_seconds"],
        )
    ]
    # Collapse characters into words
    collapsed = []
    cur = None
    for ch in words:
        if ch["word"] == " ":
            if cur:
                collapsed.append(cur)
                cur = None
            continue
        if cur is None:
            cur = {"word": ch["word"], "start": ch["start"], "end": ch["end"]}
        else:
            cur["word"] += ch["word"]
            cur["end"] = ch["end"]
    if cur:
        collapsed.append(cur)

    duration = _mp3_duration(out_path)
    return {"mp3_path": out_path, "duration_sec": duration, "words": collapsed}


def _mp3_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())
