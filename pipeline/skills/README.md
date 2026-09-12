# Vendored Remotion agent skills

Official skills from
[remotion-dev/remotion](https://github.com/remotion-dev/remotion/tree/main/packages/skills),
pinned to the commit SHA in `remotion/SHA` (fetched `remotion/FETCHED_AT`).

## What's here

- `remotion-best-practices.md` — router to the other skills; vendored for reference.
- `remotion-markup.md` — **injected into the coder agent's system prompt**
  (`agents/coder.py`, `REMOTION_SKILLS_MD`). This is the skill directly
  applicable to writing scene components: `useCurrentFrame`/`interpolate`
  patterns, spring easings, no CSS transitions, inline styles.
- `remotion-captions.md` — vendored for a future burned-in subtitles toggle
  (references `@remotion/captions`, not currently in the scene sandbox).
- `remotion-render.md` — vendored for reference; rendering is done by the
  orchestrator, not the coder.

## Sandbox conflicts

The skills assume a full Remotion project (`@remotion/media`,
`staticFile()`, `Interactive.*`). The scene sandbox is stricter (only
`react`/`remotion` imports, no network, no `<Audio>`). `coder.py` includes a
SANDBOX ADAPTER notice giving the hard constraints precedence wherever they
conflict.

## Refreshing

```bash
./skills/refresh.sh        # re-pull from GitHub, update SHA pin
modal deploy modal_app.py # ship (skills ride in the Modal image via add_local_dir)
```
