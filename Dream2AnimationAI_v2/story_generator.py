"""
story_generator.py
──────────────────
Generates a rich, emotionally compelling animation story from a user idea.
Uses caching to avoid duplicate API calls.
"""

from gemini_client import ask
from pipeline_cache import cache_get, cache_set
from logger import log


_PROMPT_TEMPLATE = """
You are a senior Pixar/DreamWorks story writer with 20 years of experience.

Write a COMPLETE, emotionally powerful animated movie story from the idea below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STORY IDEA: {idea}
GENRE: {genre}
TARGET AUDIENCE: {audience}
LANGUAGE: {language}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output structure (use these exact headings):

# 🎬 [Movie Title]

## Tagline
One punchy, memorable line.

## Setting
Time, place, and world description (2–3 sentences).

## Themes
3–5 core emotional/thematic pillars (bullet list).

## Story

### Act 1 – Ordinary World (150–200 words)
Introduce protagonist, their world, their flaw, and the inciting incident.

### Act 2 – Rising Action (200–250 words)
Protagonist encounters obstacles, allies, and deepening conflict.

### Act 3 – Climax & Resolution (150–200 words)
Emotional peak, internal breakthrough, and satisfying resolution.

## Moral / Message
One sentence capturing what the audience should feel or learn.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES:
• Use vivid, sensory language.
• Every character must have a clear flaw and arc.
• Include at least one emotionally resonant moment that could make the audience cry or cheer.
• Keep it family-friendly unless genre requires otherwise.
• Do NOT include scene numbers — this is narrative prose.
"""


def generate_story(idea: str, genre: str = "Adventure",
                   audience: str = "Kids", language: str = "English") -> str:
    """
    Generate a complete animated movie story.

    Parameters
    ----------
    idea     : user's raw story idea
    genre    : selected genre
    audience : target audience
    language : output language

    Returns
    -------
    Full story text (Markdown).
    """
    cache_key = f"{idea}|{genre}|{audience}|{language}"
    cached = cache_get("story", cache_key)
    if cached:
        return cached

    log.info("Generating story...")
    prompt = _PROMPT_TEMPLATE.format(
        idea=idea, genre=genre, audience=audience, language=language
    )
    result = ask(prompt)
    if result:
        cache_set("story", cache_key, result)
    return result
