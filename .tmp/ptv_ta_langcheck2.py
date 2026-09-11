"""Detect narration language using the deployed app's image (no rebuild)."""
import sys
sys.path.insert(0, "/home/hatch/workspace/prompt-to-video/pipeline")
import modal
from modal_app import image as ptv_image

app = modal.App("ptv-ta-langcheck2")


@app.function(image=ptv_image, volumes={"/data": modal.Volume.from_name("ptv-data")})
def main():
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    wav = "/data/79af73d7-5e25-44ce-9cbe-0b9bffa48f55/s1.wav"
    segments, info = model.transcribe(wav, beam_size=1)
    print("detected:", info.language, "prob:", round(info.language_probability, 3))
    for i, s in enumerate(segments):
        print(f"[{s.start:.0f}s]", s.text.strip()[:110])
        if i >= 2:
            break


@app.local_entrypoint()
def run():
    main.remote()
