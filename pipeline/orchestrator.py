"""Orchestrator: runs the full multi-agent pipeline for one topic.

Flow:
  planner -> architect -> visual briefs (parallel) -> TTS (parallel)
    -> code + render per scene (parallel Modal functions, each with a
       correctness retry loop) -> concat -> upload to R2 -> done

v1 deliberately has no taste critic: the coder gets full creative control.
The only guardrail is correctness — code must compile and render, otherwise
the error is fed back to the coder (up to MAX_CODE_ATTEMPTS).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import planner, architect, visual, coder  # noqa: E402
import tts  # noqa: E402

FPS = 30
MAX_CODE_ATTEMPTS = 3
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "remotion")

STYLE_GUIDE = {
    "palette": {
        "background": "#0a0a10",
        "surface": "#14141d",
        "text": "#f2f2f7",
        "muted": "#9a9ab0",
        "accent": "#7c5cff",
        "accent2": "#00d4ff",
    },
    "fonts": "system-ui, -apple-system, sans-serif for all text",
    "tone": "premium explainer-video aesthetic: generous whitespace, smooth motion, restrained color",
}


def set_stage(jobs, job_id, stage, **extra):
    state = jobs.get(job_id) or {}
    state.update({"stage": stage, **extra})
    jobs[job_id] = state


def run(job_id, topic, jobs, vol, workdir):
    """Main entrypoint, runs inside the Modal container."""
    try:
        os.makedirs(workdir, exist_ok=True)

        set_stage(jobs, job_id, "planning")
        plan = planner.plan(topic)

        set_stage(jobs, job_id, "scripting", title=plan.get("title"))
        scenes = architect.build(plan)["scenes"]

        set_stage(jobs, job_id, "storyboarding")
        with ThreadPoolExecutor(max_workers=6) as ex:
            briefs = list(ex.map(lambda s: visual.direct(s, STYLE_GUIDE), scenes))

        set_stage(jobs, job_id, "voice")
        with ThreadPoolExecutor(max_workers=6) as ex:
            audios = list(
                ex.map(
                    lambda s: tts.synthesize(
                        s["narration"], os.path.join(workdir, f"{s['id']}.mp3")
                    ),
                    scenes,
                )
            )
        vol.commit()  # make mp3s visible to the render workers

        specs = []
        for s, b, a in zip(scenes, briefs, audios):
            # Audio is the master clock: scene duration = narration + small tail.
            dur_frames = int(a["duration_sec"] * FPS) + int(0.6 * FPS)
            specs.append(
                {
                    "id": s["id"],
                    "narration": s["narration"],
                    "brief": b,
                    "words": a["words"],
                    "mp3": os.path.join(workdir, f"{s['id']}.mp3"),
                    "duration_frames": dur_frames,
                }
            )

        set_stage(jobs, job_id, "animating", sceneCount=len(specs))
        from modal_app import build_scene  # deferred: only exists on Modal

        rendered = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            # Each build_scene does codegen (with correctness retries) + render + mux.
            futures = [ex.submit(build_scene.remote, job_id, sp, workdir) for sp in specs]
            for i, f in enumerate(futures):
                set_stage(jobs, job_id, "animating", sceneCount=len(specs), sceneDone=i)
                rendered.append(f.result())

        set_stage(jobs, job_id, "assembling")
        # Scene mp4s were written by worker containers; refresh this container's
        # view of the volume before reading them (avoids stale/partial reads).
        vol.reload()
        final_mp4 = os.path.join(workdir, "final.mp4")
        _concat(rendered, final_mp4)

        set_stage(jobs, job_id, "uploading")
        url = _upload_to_r2(final_mp4, job_id)
        vol.commit()

        set_stage(jobs, job_id, "done", videoUrl=url, title=plan.get("title"))
    except Exception as e:  # noqa: BLE001
        set_stage(jobs, job_id, "error", error=str(e)[:500])
        raise


# ---------------------------------------------------------------------------
# Per-scene build: codegen (with correctness retries) -> render -> mux audio
# ---------------------------------------------------------------------------

def build_scene(job_id, spec, workdir):
    """Runs inside a Modal worker (spawned in parallel per scene)."""
    projdir = os.path.join(workdir, f"remotion-{spec['id']}")
    if os.path.exists(projdir):
        shutil.rmtree(projdir)
    # Copy the template WITHOUT node_modules (it's huge and full of symlinks
    # that copytree would flatten, breaking .bin/remotion). Symlink it instead:
    # workers only read from it during render.
    shutil.copytree(
        "/opt/remotion-template", projdir,
        ignore=shutil.ignore_patterns("node_modules"),
    )
    os.symlink(
        "/opt/remotion-template/node_modules",
        os.path.join(projdir, "node_modules"),
    )
    scene_file = os.path.join(projdir, "src", "scenes", "Scene.tsx")
    os.makedirs(os.path.dirname(scene_file), exist_ok=True)

    last_error = None
    last_code = None
    for attempt in range(1, MAX_CODE_ATTEMPTS + 1):
        code = coder.write_scene(
            scene=spec,
            brief=spec["brief"],
            narration=spec["narration"],
            words=spec["words"],
            duration_frames=spec["duration_frames"],
            fps=FPS,
            style_guide=STYLE_GUIDE,
            previous_code=last_code,
            previous_error=last_error,
        )
        with open(scene_file, "w") as f:
            f.write(code)
        _write_root(projdir, spec["id"], spec["duration_frames"])

        silent_mp4 = os.path.join(workdir, f"{spec['id']}-silent.mp4")
        ok, err = _remotion_render(projdir, spec["id"], spec["duration_frames"], silent_mp4)
        if ok and os.path.exists(silent_mp4) and os.path.getsize(silent_mp4) > 50_000:
            final = os.path.join(workdir, f"{spec['id']}.mp4")
            _mux_audio(silent_mp4, spec["mp3"], final)
            return final
        last_error, last_code = err, code

    raise RuntimeError(f"Scene {spec['id']} failed to render after {MAX_CODE_ATTEMPTS} attempts: {last_error[:500]}")


def _write_root(projdir, scene_id, duration_frames):
    root = f"""import {{Composition}} from 'remotion';
import {{Scene}} from './scenes/Scene';

export const RemotionRoot = () => (
  <>
    <Composition
      id="{scene_id}"
      component={{Scene}}
      durationInFrames={{{duration_frames}}}
      fps={{{FPS}}}
      width={{1920}}
      height={{1080}}
    />
  </>
);
"""
    with open(os.path.join(projdir, "src", "Root.tsx"), "w") as f:
        f.write(root)


def _remotion_render(projdir, comp_id, duration_frames, out_path):
    try:
        proc = subprocess.run(
            ["npx", "remotion", "render", comp_id, out_path, "--overwrite"],
            cwd=projdir,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        if proc.returncode == 0:
            return True, ""
        return False, (proc.stderr or proc.stdout)[-3000:]
    except subprocess.TimeoutExpired:
        return False, "render timed out"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def _mux_audio(silent_mp4, mp3, out):
    subprocess.run(
        ["ffmpeg", "-y", "-i", silent_mp4, "-i", mp3,
         "-c:v", "copy", "-c:a", "aac", "-shortest", out],
        capture_output=True, check=True,
    )


def _concat(mp4s, out, attempts=3):
    last_err = ""
    for a in range(attempts):
        lst = tempfile.mktemp(suffix=".txt")
        with open(lst, "w") as f:
            for p in mp4s:
                f.write(f"file '{p}'\n")
        proc = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
             "-c:v", "libx264", "-preset", "fast", "-crf", "20",
             "-c:a", "aac", out],
            capture_output=True, text=True,
        )
        if proc.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 100_000:
            return
        last_err = (proc.stderr or proc.stdout or "")[-2000:]
        time.sleep(10)
    raise RuntimeError(f"ffmpeg concat failed after {attempts} attempts: {last_err[:1500]}")


def _upload_to_r2(path, job_id):
    import boto3

    bucket = os.environ["R2_BUCKET"]
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_KEY_ID"],
        aws_secret_access_key=os.environ["R2_KEY_SECRET"],
        region_name="auto",
    )
    key = f"videos/{job_id}.mp4"
    s3.upload_file(path, bucket, key, ExtraArgs={"ContentType": "video/mp4"})
    return f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{key}"
