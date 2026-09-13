"""Modal deployment for the prompt-to-video pipeline.

Deploy with:  modal deploy pipeline/modal_app.py
Secrets needed (modal secret create ptv-secrets):
  LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,   (TTS also uses the OpenRouter key)
  R2_ENDPOINT, R2_KEY_ID, R2_KEY_SECRET, R2_BUCKET, R2_PUBLIC_BASE,
  PTV_WEBHOOK_SECRET
"""
import os
import sys
import time

import modal
from fastapi import Header, HTTPException

app = modal.App("prompt-to-video")

image = (
    modal.Image.from_registry("node:20-bookworm-slim", add_python="3.11")
    .apt_install("ffmpeg", "chromium", "fonts-noto-core")
    # Tamil glyphs must ALWAYS render (Debian's fonts-noto-core coverage varies):
    # bake Noto Sans Tamil into the image explicitly so Chromium fallback is deterministic.
    .run_commands(
        "mkdir -p /usr/share/fonts/truetype/noto-tamil && "
        "python3 -c \"import urllib.request; urllib.request.urlretrieve("
        "'https://github.com/google/fonts/raw/main/ofl/notosanstamil/NotoSansTamil%5Bwdth,wght%5D.ttf', "
        "'/usr/share/fonts/truetype/noto-tamil/NotoSansTamil.ttf')\" && "
        "fc-cache -f >/dev/null && (fc-list | grep -ci tamil || true)"
    )
    .pip_install("requests", "boto3", "fastapi[standard]", "faster-whisper")
    .run_commands(
        "python3 -c \"from faster_whisper import WhisperModel; "
        "WhisperModel('base', device='cpu', compute_type='int8')\""
    )
    .add_local_dir("remotion", "/opt/remotion-template", copy=True)
    .run_commands("cd /opt/remotion-template && npm install --no-audit --no-fund")
    .add_local_dir(".", "/opt/pipeline")
)

vol = modal.Volume.from_name("ptv-data", create_if_missing=True)
jobs = modal.Dict.from_name("ptv-jobs", create_if_missing=True)


def _authorized(authorization: str | None) -> bool:
    expected = os.environ.get("PTV_WEBHOOK_SECRET", "")
    if not expected:
        return True
    return authorization == f"Bearer {expected}"


@app.function(image=image, volumes={"/data": vol}, timeout=3600,
              secrets=[modal.Secret.from_name("ptv-secrets")])
def run_pipeline(job_id: str, topic: str, lang: str = "en", mode: str = "short"):
    sys.path.insert(0, "/opt/pipeline")
    from orchestrator import run
    run(job_id, topic, jobs, vol, f"/data/{job_id}", lang, mode)


@app.function(image=image, volumes={"/data": vol}, timeout=1800,
              secrets=[modal.Secret.from_name("ptv-secrets")])
def build_scene(job_id: str, spec: dict, workdir: str) -> tuple:
    sys.path.insert(0, "/opt/pipeline")
    from orchestrator import build_scene as _build
    return _build(job_id, spec, workdir)


@app.function(image=image, secrets=[modal.Secret.from_name("ptv-secrets")])
@modal.fastapi_endpoint(method="POST")
def generate(data: dict, authorization: str | None = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="unauthorized")
    job_id = data.get("jobId")
    topic = (data.get("topic") or "").strip()
    lang = data.get("lang", "en")
    if lang not in ("en", "ta"):
        lang = "en"
    mode = data.get("mode", "short")
    if mode not in ("reel", "short", "deep"):
        mode = "short"
    if not job_id or not topic:
        raise HTTPException(status_code=400, detail="jobId and topic required")
    jobs[job_id] = {"stage": "queued", "lang": lang, "mode": mode, "topic": topic,
                    "createdAt": int(time.time())}
    run_pipeline.spawn(job_id, topic, lang, mode)
    return {"jobId": job_id}


@app.function(image=image, secrets=[modal.Secret.from_name("ptv-secrets")])
@modal.fastapi_endpoint(method="GET")
def list_jobs(authorization: str | None = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="unauthorized")
    out = []
    for k in jobs.keys():
        try:
            v = dict(jobs[k])
        except Exception:
            continue
        out.append({
            "jobId": k,
            "title": v.get("title") or v.get("topic") or "Untitled",
            "stage": v.get("stage"),
            "lang": v.get("lang") or "en",
            "mode": v.get("mode") or "short",
            "createdAt": v.get("createdAt"),
            "videoUrl": v.get("videoUrl"),
            "error": (v.get("error") or "")[:200],
            "sceneDone": v.get("sceneDone"),
            "sceneCount": v.get("sceneCount"),
        })
    out.sort(key=lambda r: r["createdAt"] or 0, reverse=True)
    return {"jobs": out[:20]}


@app.function(image=image, secrets=[modal.Secret.from_name("ptv-secrets")])
@modal.fastapi_endpoint(method="GET")
def status(jobId: str, authorization: str | None = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="unauthorized")
    state = jobs.get(jobId)
    if not state:
        raise HTTPException(status_code=404, detail="unknown job")
    return dict(state)
