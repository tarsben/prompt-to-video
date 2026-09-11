"""Patch the manually-spawned Tamil job's lang to 'ta' for accurate history."""
import modal

app = modal.App("ptv-fix-lang")


@app.function()
def main():
    d = modal.Dict.from_name("ptv-jobs")
    k = "79af73d7-5e25-44ce-9cbe-0b9bffa48f55"
    rec = dict(d[k])
    rec["lang"] = "ta"
    d[k] = rec
    print("patched", k, "->", dict(d[k]).get("lang"))


@app.local_entrypoint()
def run():
    main.remote()
