"""List files in the Tamil job's workdir on the volume."""
import modal

app = modal.App("ptv-ta-vol")


@app.function(volumes={"/data": modal.Volume.from_name("ptv-data")})
def main():
    import os
    base = "/data/79af73d7-5e25-44ce-9cbe-0b9bffa48f55"
    for root, dirs, files in os.walk(base):
        level = root.replace(base, "").count(os.sep)
        if level > 2:
            continue
        print("  " * level + os.path.basename(root) + "/")
        for f in sorted(files)[:20]:
            fp = os.path.join(root, f)
            print("  " * (level + 1) + f, os.path.getsize(fp))


@app.local_entrypoint()
def run():
    main.remote()
