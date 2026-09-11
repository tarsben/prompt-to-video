"""Agent 4 — Coder. Scene + visual brief -> Remotion React component.

The coder gets FULL creative control: it writes the actual animation code.
The only guardrail is a correctness loop in the orchestrator (code must compile
and render; failures are fed back for up to 3 attempts). No taste critic in v1.
"""
from llm import chat, model_for

SYSTEM = """You are an expert motion-graphics developer working in Remotion
(React-based programmatic video, v4 API). Write a single self-contained scene component.

HARD CONSTRAINTS — violating any of these is a failure:
- Output ONLY TypeScript React code. No markdown, no explanation.
- Declare the component with a NAMED export exactly like this:
  `export const Scene: React.FC = () => {{ ... }};`
  Do NOT use `export default`. The entrypoint imports it as `import {{Scene}} from './scenes/Scene'`.
- imports allowed: 'react', 'remotion' (AbsoluteFill, Sequence, spring, interpolate,
  useCurrentFrame, useVideoConfig, Easing, etc.). Nothing else.
- Resolution 1920x1080, {fps} FPS, EXACTLY {duration_frames} frames. Choreograph every
  animation to this duration; the final frame must look intentional, never cut off.
- Zero network requests, zero external images/video/fonts. Everything is drawn in code:
  divs, SVG, CSS. System font stack only.
- No <Audio> elements — narration is muxed separately.
- Must compile under `tsc --noEmit` strict.

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
This is your canvas — make it beautiful.
Return ONLY the code."""


def write_scene(scene, brief, narration, words, duration_frames, fps, style_guide,
                previous_code=None, previous_error=None):
    import json
    system = SYSTEM.format(fps=fps, duration_frames=duration_frames)
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
        max_tokens=6000,
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
