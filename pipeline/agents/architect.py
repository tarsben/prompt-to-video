"""Agent 2 — Scene architect. Learning arc -> scenes with narration scripts."""
from llm import chat, model_for

BASE = """You turn a lesson plan into video scenes. Each scene is one continuous shot
of spoken narration. Write narration that sounds like a great teacher speaking —
conversational, concrete, no jargon without explanation.

Return JSON only:
{
  "scenes": [
    {"id": "s1", "beat_id": "b1",
     "purpose": "what this scene accomplishes",
     "narration": "the exact words to be spoken"}
  ]
}
Rules:
- The first scene must hook the viewer fast.
- The last scene lands the takeaway.
- You have live web search: verify any facts, figures, names, or dates in the
  narration; never invent statistics."""

MODE_SPECS = {
    "reel": {
        "brief": "REEL MODE: 3 to 4 scenes total (a beat may span 1-2 scenes), each scene "
                 "30-50 words of narration (~15-20 seconds spoken). Total video about "
                 "60 seconds. Fast, punchy, zero filler.",
        "max_tokens": 3000,
    },
    "short": {
        "brief": "SHORT MODE: 6 to 10 scenes total (a beat may span 1-2 scenes), each scene "
                 "40-90 words of narration (~20-40 seconds spoken). Total video about 5 minutes.",
        "max_tokens": 8000,
    },
    "deep": {
        "brief": "DEEP DIVE MODE: 14 to 22 scenes total, each scene 60-120 words of narration "
                 "(~30-60 seconds spoken). Total video 15-22 minutes. Cover the beats "
                 "thoroughly — a beat may span several scenes. Keep momentum: vary the "
                 "examples, and return to the core intuition between technical stretches.",
        "max_tokens": 16000,
    },
}


def build(plan, lang="en", mode="short", notes=""):
    import json
    spec = MODE_SPECS.get(mode, MODE_SPECS["short"])
    system = BASE + "\n\n" + spec["brief"]
    if notes.strip():
        system += ("\n\nThe user gave these extra instructions for this video — "
                   "follow them while writing the scenes:\n" + notes.strip())
    if lang == "ta":
        system += (
            "\n\nThe narration must be written in Tamil (Tamil script), sounding like"
            " a great Tamil teacher speaking — conversational, concrete, no jargon"
            " without explanation. Keep purpose/id/beat_id in English; only the"
            " \"narration\" field is in Tamil."
        )
    return chat(system, f"Lesson plan:\n{json.dumps(plan)}", model=model_for("architect"),
                max_tokens=spec["max_tokens"], temperature=0.7, web_search=True)
