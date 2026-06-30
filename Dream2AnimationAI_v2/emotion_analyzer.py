"""
emotion_analyzer.py
───────────────────
Analyzes the emotional arc of the story and returns a structured profile
used by music_generator and the UI.
"""

from gemini_client import ask
from pipeline_cache import cache_get, cache_set
from logger import log


_PROMPT = """
You are a professional Film Emotion Analyst.

Read the story and output a detailed emotional analysis.

Return ONLY in this Markdown format (no extra text):

## Overall Emotion
[Single dominant emotion, e.g. Hope, Wonder, Melancholy, Triumph]

## Emotional Arc
- Opening: [emotion at start]
- Rising Action: [emotion building]
- Climax: [peak emotion]
- Resolution: [closing emotion]

## Primary Emotion
[one word]

## Secondary Emotion
[one word]

## Mood
[one word, e.g. Whimsical, Dark, Uplifting, Bittersweet]

## Audience Feeling
[How the audience should feel at the end — one sentence]

## Music Direction
- Genre: [e.g. Orchestral, Ambient, Epic, Whimsical]
- Tempo: [Slow | Medium | Fast | Variable]
- Key Instruments: [3-4 instruments]
- Opening Theme: [describe opening music mood]
- Climax Theme: [describe climax music]
- Closing Theme: [describe closing music mood]

Story:
{story}
"""


def analyze_emotion(story: str) -> str:
    """Analyze story emotion and return structured markdown."""
    cached = cache_get("emotion", story[:200])
    if cached:
        return cached

    log.info("Analyzing story emotion...")
    result = ask(_PROMPT.format(story=story), fast=True)
    if result:
        cache_set("emotion", story[:200], result)
    return result
