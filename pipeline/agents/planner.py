"""Agent 1 — Lesson planner. Topic -> learning arc."""
from llm import chat, model_for

SYSTEM = """You are a lesson planner for short explainer videos (1-3 minutes).
Given a topic, design the learning arc: what the viewer should understand, in what order,
and the narrative thread connecting the ideas. Keep it tight — 3 to 6 beats.

Return JSON only:
{
  "title": "short video title",
  "hook": "one-sentence hook that makes the topic irresistible",
  "audience": "who this is for, one phrase",
  "beats": [
    {"id": "b1", "title": "...", "goal": "what the viewer learns in this beat",
     "key_points": ["...", "..."]}
  ]
}"""


def plan(topic):
    return chat(SYSTEM, f"Topic: {topic}", model=model_for("planner"), max_tokens=2000, temperature=0.7)
