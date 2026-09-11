"""Detect language of the Tamil job's scene-1 narration."""
import modal

app = modal.App("ptv-ta-langcheck")

# Reuse the deployed image (has faster-whisper + base model cached)
image = (
    modal.Image.from_registry("node:20-bookworm-slim", add_python="3.11")
    .pip_install("faster-whisper")
    .run_commands(
        "python3 -c \"from faster_whisper import WhisperModel; "
        "WhisperModel('base', device='cpu', compute_type='int8')\""
    )
)


@app.function(image=image, volumes={"/data": modal.Volume.from_name("ptv-data")})
def main():
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    wav = "/data/79af73d7-5e25-44ce-9cbe-0b9bffa48f55/s1.wav"
    # language detection on first 30s
    segments, info = model.transcribe(wav, beam_size=1)
    print("detected:", info.language, "prob:", round(info.language_probability, 3))
    for i, s in enumerate(segments):
        print(f"[{s.start:.1f}-{s.end:.1f}]", s.text.strip()[:120])
        if i >= 2:
            break


@app.local_entrypoint()
def run():
    main.remote()
