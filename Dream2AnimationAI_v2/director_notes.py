"""
director_notes.py
─────────────────
Generates professional director's notes covering visual style, lighting,
colour palette, animation direction, and special effects.
"""

from gemini_client import ask
from pipeline_cache import cache_get, cache_set
from logger import log


_PROMPT = """
You are a veteran Pixar/DreamWorks Animation Film Director.

Read the story and write professional director notes.

Return ONLY in this Markdown format:

## 🎬 Director's Vision
[2 sentences on overall artistic intent]

## 🎨 Animation Style
- Render Style: [e.g. Pixar 3D, DreamWorks stylized, watercolor 2D]
- Character Design: [broad adjective + reference style]
- World Design: [environment feel]

## 💡 Lighting
- Overall: [e.g. warm golden hour, cool moonlight, harsh contrast]
- Key Scenes: [specific lighting notes per story beat]

## 🌈 Color Palette
- Protagonist's World: [palette]
- Antagonist/Conflict World: [palette]
- Resolution: [palette]

## 📷 Signature Camera Moves
[List 3-5 specific shots you want in this film]

## 😊 Character Expression Guidelines
[How expressions should be amplified for animation]

## 🌍 Background Design
[World-building and environment notes]

## ✨ Special Effects
[Particle effects, magic, weather, lighting FX]

## 🎵 Music & Sound Notes
[Orchestration notes and key sound design moments]

Story:
{story}
"""


def generate_director_notes(story: str) -> str:
    """Generate professional director notes for the story."""
    cached = cache_get("director_notes", story[:200])
    if cached:
        return cached

    log.info("Generating director notes...")
    result = ask(_PROMPT.format(story=story), fast=True)
    if result:
        cache_set("director_notes", story[:200], result)
    return result
