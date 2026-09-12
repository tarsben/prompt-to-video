"""Agent 4 — Coder. Scene + visual brief -> Remotion React component.

The coder gets FULL creative control: it writes the actual animation code.
The only guardrail is a correctness loop in the orchestrator (code must compile
and render; failures are fed back for up to 3 attempts). No taste critic in v1.

Official Remotion agent skills are vendored in pipeline/skills/remotion/ and the
remotion-markup skill is injected into the system prompt (see REMOTION_SKILLS_MD)
so generated scenes follow Remotion's own idioms. Only remotion-markup is
injected: it is the skill directly applicable to writing scene components.
remotion-best-practices is mostly a router to other skills; remotion-captions
and remotion-render are vendored for future use (subtitles toggle, render
upgrades) but reference packages/APIs outside the scene sandbox.
"""
import os as _os
import re as _re

from llm import chat, model_for

_SKILL_DIR = _os.path.join(_os.path.dirname(__file__), "..", "skills", "remotion")


def _load_skill(name):
    """Load a vendored Remotion agent skill, stripping its YAML frontmatter."""
    try:
        with open(_os.path.join(_SKILL_DIR, name + ".md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return ""
    return _re.sub(r"^---\n.*?\n---\n", "", text, count=1,
                   flags=_re.DOTALL).strip()


# Injected into SYSTEM via the {remotion_skills} placeholder in write_scene's
# str.format() call. Passed as a format *value*, so the skill's own curly braces
# are inserted literally and never interpreted.
REMOTION_SKILLS_MD = _load_skill("remotion-markup")

SYSTEM = """You are an expert motion-graphics developer working in Remotion
(React-based programmatic video, v4 API). Write a single self-contained scene component.

HARD CONSTRAINTS — violating any of these is a failure:
- Output ONLY TypeScript React code. No markdown, no explanation.
- Declare the component with a NAMED export exactly like this:
  `export const Scene: React.FC = () => {{ ... }};`
  Do NOT use `export default`. The entrypoint imports it as `import {{Scene}} from './scenes/Scene'`.
- imports allowed: 'react', 'remotion' (AbsoluteFill, Sequence, spring, interpolate,
  useCurrentFrame, useVideoConfig, Easing, etc.). Nothing else.
- Resolution {width}x{height}, {fps} FPS, EXACTLY {duration_frames} frames. Choreograph every
  animation to this duration; the final frame must look intentional, never cut off.
{layout_note}
- Zero network requests, zero external images/video/fonts. Everything is drawn in code:
  divs, SVG, CSS. System font stack only.
- No <Audio> elements — narration is muxed separately.
- Must compile under `tsc --noEmit` strict.

OFFICIAL REMOTION GUIDANCE (from Remotion's own agent skill — follow these idioms):
{remotion_skills}

SANDBOX ADAPTER — where the guidance above conflicts with the HARD CONSTRAINTS,
the HARD CONSTRAINTS win. Concretely: no @remotion/* packages beyond 'remotion'
itself, no staticFile(), no <Audio>/<Video>/<CanvasImage>/<AnimatedImage>
elements, no Interactive.* wrappers, no Tailwind, no CSS transitions or keyframe
animations. Drive ALL motion with useCurrentFrame() + interpolate() exactly as
the guidance describes.

TIMED NARRATION (the voiceover for this exact scene):
"{{narration}}"

Word timestamps (seconds, use these to time reveals, highlights, and animation beats
to the spoken words):
{{words_json}}

VISUAL BRIEF (your creative direction — interpret it with flair, don't just execute literally):
{{brief_json}}

STYLE GUIDE (shared across scenes for continuity):
{{style_json}}

Craft bar: the polish of a top-tier YouTube explainer. Generous whitespace, spring-based
motion, restrained palette, kinetic typography that lands on the spoken words.
BUDGET: you have a hard output token limit. A complete, slightly simpler scene beats
an ambitious truncated one — ALWAYS finish the file with every tag and brace closed.
This is your canvas — make it beautiful.
Return ONLY the code."""


def write_scene(scene, brief, narration, words, duration_frames, fps, style_guide,
                previous_code=None, previous_error=None, width=1920, height=1080):
    import json
    if height > width:
        layout_note = (
            "VERTICAL 9:16 canvas (phone fullscreen). Compose for portrait: stack content "
            "vertically, keep key visuals and text inside the central 60% of the frame "
            "(top and bottom are covered by app UI), use large type (nothing important "
            "below ~56px), avoid wide side-by-side layouts."
        )
    else:
        layout_note = ""
    system = SYSTEM.format(fps=fps, duration_frames=duration_frames,
                           width=width, height=height, layout_note=layout_note,
                           remotion_skills=REMOTION_SKILLS_MD)
    user = (
        f'NARRATION: "{narration}"\n\n'
        f"WORD_TIMESTAMPS: {json.dumps(words)}\n\n"
        f"VISUAL_BRIEF: {json.dumps(brief)}\n\n"
        f"STYLE_GUIDE: {json.dumps(style_guide)}"
    )
    if previous_error:
        user += (
            "\n\nYOUR PREVIOUS ATTEMPT FAILED. Here is the code you wrote:\n"
            f"{previous_code}\n\nAnd here is the error:\n{previous_error}\n\n"
            "Fix the problem and return the complete corrected component. "
            "Return ONLY the code."
        )
    # system already carries the dynamic fields; pass the rest as user content
    code = chat(
        system.replace("{narration}", narration)
        .replace("{words_json}", json.dumps(words))
        .replace("{brief_json}", json.dumps(brief))
        .replace("{style_json}", json.dumps(style_guide)),
        user,
        json_mode=False,
        model=model_for("coder"),
        max_tokens=16000,
        temperature=0.8,
    )
    return _strip_fences(code)


def _strip_fences(code):
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        code = "\n".join(lines)
    return code.strip()
