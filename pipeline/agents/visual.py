"""Agent 3 — Visual director. Scene -> creative visual brief."""
from llm import chat

SYSTEM = """You are the visual director for an animated explainer video. For each scene you
receive, write a creative brief describing exactly what the viewer sees and how it moves.
Think like a motion designer: composition, pacing of reveals, color, mood, kinetic
typography, diagrams that build step by step.

Return JSON only:
{
  "setting": "one-line description of the scene's visual world",
  "mood": "e.g. curious, dramatic, playful",
  "palette": ["#hex1", "#hex2", "#hex3"],
  "elements": ["each visual element that appears, in order"],
  "motion": ["how elements enter, move, and exit — beat by beat"],
  "on_screen_text": ["short labels or phrases shown on screen (not the narration)"]
}
Rules:
- Design for 1920x1080. Everything must be drawable in code (shapes, text, SVG) —
  no stock photos, no external assets.
- On-screen text is sparse: labels and punchlines only, never full narration.
- Keep visual continuity with the style guide provided."""


def direct(scene, style_guide):
    import json
    user = (
        f"Style guide:\n{json.dumps(style_guide)}\n\n"
        f"Scene:\n{json.dumps(scene)}"
    )
    return chat(SYSTEM, user, max_tokens=2000, temperature=0.8)
