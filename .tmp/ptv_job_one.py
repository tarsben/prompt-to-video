"""Full record for one job id prefix."""
import modal

app = modal.App("ptv-job-one")


@app.function()
def main(prefix: str):
    import json
    d = modal.Dict.from_name("ptv-jobs")
    for k in d.keys():
        if k.startswith(prefix):
            print(json.dumps({k: dict(d[k])}, indent=2, default=str)[:3000])
            return
    print("not found: " + prefix)


@app.local_entrypoint()
def run(prefix: str = "79af73d7"):
    main.remote(prefix=prefix)
