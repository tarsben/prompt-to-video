"""Agent 2 — Scene architect. Learning arc -> scenes with narration scripts."""
from llm import chat

SYSTEM = """You turn a lesson plan into video scenes. Each scene is one continuous shot,
roughly 15-40 seconds of spoken narration. Write narration that sounds like a great
teacher speaking — conversational, concrete, no jargon without explanation.

Return JSON only:
{
  "scenes": [
    {"id": "s1", "beat_id": "b1",
     "purpose": "what this scene accomplishes",
     "narration": "the exact words to be spoken (40-90 words)"}
  ]
}
Rules:
- 3 to 6 scenes total, matching the beats (a beat may span 1-2 scenes).
- The first scene must hook the viewer in under 10 seconds.
- The last scene lands the takeaway."""


def build(plan):
    import json
    return chat(SYSTEM, f"Lesson plan:\n{json.dumps(plan)}", max_tokens=3000, temperature=0.7)
