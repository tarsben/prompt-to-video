"""Modal deployment for the prompt-to-video pipeline.

Deploy with:  modal deploy pipeline/modal_app.py
Secrets needed (modal secret create ptv-secrets):
  LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
  ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
  R2_ENDPOINT, R2_KEY_ID, R2_KEY_SECRET, R2_BUCKET, R2_PUBLIC_BASE,
  PTV_WEBHOOK_SECRET
"""
import os
import sys

import modal

app = modal.App("prompt-to-video")

image = (
    modal.Image.from_registry("node:20-bookworm-slim", add_python="3.11")
    .apt_install("ffmpeg", "chromium")
    .pip_install("requests", "boto3", "elevenlabs", "fastapi[standard]")
    .add_local_dir("remotion", "/opt/remotion-template", copy=True)
    .run_commands("cd /opt/remotion-template && npm install --no-audit --no-fund")
    .add_local_dir(".", "/opt/pipeline")
)

vol = modal.Volume.from_name("ptv-data", create_if_missing=True)
jobs = modal.Dict.from_name("ptv-jobs", create_if_missing=True)


def _authorized(request):
    expected = os.environ.get("PTV_WEBHOOK_SECRET", "")
    if not expected:
        return True
    return request.headers.get("authorization") == f"Bearer {expected}"


@app.function(image=image, volumes={"/data": vol}, timeout=3600,
              secrets=[modal.Secret.from_name("ptv-secrets")])
def run_pipeline(job_id: str, topic: str):
    sys.path.insert(0, "/opt/pipeline")
    from orchestrator import run
    run(job_id, topic, jobs, vol, f"/data/{job_id}")


@app.function(image=image, volumes={"/data": vol}, timeout=1800,
              secrets=[modal.Secret.from_name("ptv-secrets")])
def build_scene(job_id: str, spec: dict, workdir: str) -> str:
    sys.path.insert(0, "/opt/pipeline")
    from orchestrator import build_scene as _build
    return _build(job_id, spec, workdir)


@app.function(image=image, secrets=[modal.Secret.from_name("ptv-secrets")])
@modal.fastapi_endpoint(method="POST")
def generate(data: dict, request):
    from fastapi import Request  # noqa
    if not _authorized(request):
        return {"error": "unauthorized"}, 401
    job_id = data.get("jobId")
    topic = (data.get("topic") or "").strip()
    if not job_id or not topic:
        return {"error": "jobId and topic required"}, 400
    jobs[job_id] = {"stage": "queued"}
    run_pipeline.spawn(job_id, topic)
    return {"jobId": job_id}


@app.function(image=image, secrets=[modal.Secret.from_name("ptv-secrets")])
@modal.fastapi_endpoint(method="GET")
def status(request):
    if not _authorized(request):
        return {"error": "unauthorized"}, 401
    job_id = request.query_params.get("jobId")
    state = jobs.get(job_id)
    if not state:
        return {"stage": "unknown"}, 404
    return dict(state)
