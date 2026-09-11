import modal, subprocess
app = modal.App("ptv-fontcheck")
image = (modal.Image.from_registry("node:20-bookworm-slim", add_python="3.11")
         .apt_install("ffmpeg", "chromium", "fonts-noto-core"))
@app.function(image=image)
def check():
    out = subprocess.run(["fc-list", ":lang=ta", "family"], capture_output=True, text=True)
    fams = sorted(set(out.stdout.split("\n")))
    print("TAMIL FAMILIES:", [f for f in fams if f][:8])
    # render a Tamil string with chromium? just confirm coverage:
    out2 = subprocess.run(["fc-match", ":lang=ta", "family"], capture_output=True, text=True)
    print("FC-MATCH ta:", out2.stdout.strip())
