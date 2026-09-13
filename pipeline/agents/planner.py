"""Agent 1 — Lesson planner. Topic -> learning arc."""
from llm import chat, model_for

BASE = """You are a lesson planner for explainer videos.
Given a topic, design the learning arc: what the viewer should understand, in what order,
and the narrative thread connecting the ideas.
You have live web search: use it to verify key facts, figures, names, dates, and any
recent developments relevant to the topic. Prefer current, accurate information over
memory; never invent statistics.

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

MODE_SPECS = {
    "reel": {
        "brief": "MODE: this is a ~60 second vertical REEL (phone fullscreen, 9:16). "
                 "Keep it tight — 3 to 4 beats, ONE punchy idea per beat. Hook in the "
                 "first 3 seconds, no slow buildup, no recap — end on a satisfying payoff line.",
        "max_tokens": 2000,
    },
    "short": {
        "brief": "MODE: this is a ~5 minute explainer video (16:9). 6 to 10 beats: hook, "
                 "build the core ideas step by step with one concrete example each, "
                 "then land the takeaway.",
        "max_tokens": 3000,
    },
    "deep": {
        "brief": "MODE: this is a ~20 minute DEEP DIVE (16:9). 14 to 22 beats organized "
                 "into clear chapters: foundations, how it really works under the hood, "
                 "edge cases and nuances, common misconceptions, and real-world "
                 "implications. Go genuinely in depth — this viewer wants the full "
                 "picture, not the highlights.",
        "max_tokens": 6000,
    },
}


def plan(topic, mode="short"):
    spec = MODE_SPECS.get(mode, MODE_SPECS["short"])
    system = BASE + "\n\n" + spec["brief"]
    return chat(system, f"Topic: {topic}", model=model_for("planner"),
                max_tokens=spec["max_tokens"], temperature=0.7, web_search=True)
