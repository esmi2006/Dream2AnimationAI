"""
storyboard_generator.py
───────────────────────
Generates a professional storyboard with every field required for the pipeline:
image prompt, animation prompt, dialogue, camera, sound, music mood, etc.

Returns both a display-friendly Markdown string AND a structured list of
scene dicts that downstream modules (image, voice, animation) consume.

Public API
----------
    generate_storyboard(story, characters, num_scenes) -> dict
        {
          "display_text": str,     # markdown for UI
          "scenes": [              # structured list
            {
              "scene_number": int,
              "title": str,
              "location": str,
              "time_of_day": str,
              "characters_present": [str],
              "character_actions": str,
              "facial_expressions": str,
              "camera_angle": str,
              "camera_movement": str,
              "image_prompt": str,          # 60-90 word cinematic prompt
              "animation_prompt": str,      # motion/animation description
              "dialogue": str,              # raw dialogue block
              "sound_effects": str,
              "music_mood": str,
              "transition": str,
            }
          ]
        }
"""

import json
import re
from gemini_client import ask
from pipeline_cache import cache_get, cache_set
from logger import log
from config import NUM_SCENES


_STORYBOARD_PROMPT = """
You are a senior Pixar/DreamWorks storyboard director.

Read the story and character profiles.
Generate EXACTLY {num_scenes} scenes for an animated movie.

Return ONLY a valid JSON array — no markdown fences, no preamble, no extra text.

Each element must follow this EXACT schema:

[
  {{
    "scene_number": 1,
    "title": "Short evocative scene title",
    "location": "Specific location name",
    "time_of_day": "Dawn | Morning | Afternoon | Dusk | Night",
    "characters_present": ["Name1", "Name2"],
    "character_actions": "What each character is physically doing — 20-30 words",
    "facial_expressions": "Expression for each character — 15-20 words",
    "camera_angle": "Eye Level | Low Angle | High Angle | Bird's Eye | Dutch Angle",
    "camera_movement": "Dolly In | Dolly Out | Pan Left | Pan Right | Crane Up | Orbit | Handheld | Static | Tracking | Zoom In | Zoom Out",
    "image_prompt": "DETAILED cinematic image prompt for AI image generation — 70-100 words. Must describe: setting, lighting, atmosphere, character positions and appearance, foreground/background, color palette, film style (e.g. Pixar 3D render, soft volumetric lighting). Include 'cinematic composition, depth of field, photorealistic animated film still' at the end.",
    "animation_prompt": "Motion description for this scene — 30-40 words. Include character movement, environmental animation (wind, water, leaves), camera motion, and mood.",
    "dialogue": "Character Name:\\nSpoken line here.\\n\\nCharacter Name:\\nSpoken line here.",
    "sound_effects": "Comma-separated ambient and action sounds e.g. 'rustling leaves, distant thunder, footsteps on gravel'",
    "music_mood": "Single word mood e.g. Joyful | Tense | Melancholic | Heroic | Mysterious | Peaceful | Dramatic",
    "transition": "Cut | Fade In | Fade Out | Dissolve | Wipe"
  }}
]

CHARACTER VISUAL DNA (inject into image prompts):
{character_dna}

STORY:
{story}

RULES:
• Generate EXACTLY {num_scenes} scenes.
• Image prompts MUST include character visual DNA for every character present.
• Each scene must visually advance the story.
• Alternate camera angles — never use the same angle twice in a row.
• Include environmental storytelling in every image prompt.
• Dialogue must be natural, short (1-2 sentences per character), and emotional.
• Return ONLY the raw JSON array.
"""


def _build_character_dna_block(characters: list) -> str:
    lines = []
    for c in characters:
        lines.append(f"• {c['name']}: {c.get('visual_dna', '')}")
    return "\n".join(lines) if lines else "(No character profiles provided)"


def generate_storyboard(story: str, characters: list,
                        num_scenes: int = NUM_SCENES) -> dict:
    """
    Generate a full storyboard.

    Parameters
    ----------
    story      : full story text
    characters : list of character dicts from character_generator
    num_scenes : number of scenes to generate

    Returns
    -------
    dict with "display_text" (markdown) and "scenes" (list of dicts)
    """
    cache_key = story[:150] + str(num_scenes)
    cached = cache_get("storyboard", cache_key)
    if cached:
        return cached

    log.info(f"Generating {num_scenes}-scene storyboard...")
    dna_block = _build_character_dna_block(characters)
    prompt = _STORYBOARD_PROMPT.format(
        num_scenes=num_scenes,
        character_dna=dna_block,
        story=story,
    )
    raw = ask(prompt)
    raw = re.sub(r"```(?:json)?|```", "", raw).strip()

    scenes = []
    try:
        scenes = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning(f"Storyboard JSON parse error: {e}. Attempting repair...")
        # Try to extract the array even if there's trailing garbage
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                scenes = json.loads(match.group(0))
            except Exception:
                log.error("Storyboard JSON unrecoverable.")

    display_lines = ["# 🎬 Storyboard\n"]
    for s in scenes:
        n = s.get("scene_number", "?")
        display_lines.append(f"---\n## Scene {n}: {s.get('title', '')}")
        display_lines.append(f"**📍 Location:** {s.get('location', '')} | "
                             f"**🕐 Time:** {s.get('time_of_day', '')}")
        display_lines.append(f"**👥 Characters:** {', '.join(s.get('characters_present', []))}")
        display_lines.append(f"**🎭 Actions:** {s.get('character_actions', '')}")
        display_lines.append(f"**😊 Expressions:** {s.get('facial_expressions', '')}")
        display_lines.append(f"**📷 Camera:** {s.get('camera_angle', '')} — "
                             f"{s.get('camera_movement', '')}")
        display_lines.append(f"**🖼 Image Prompt:** {s.get('image_prompt', '')}")
        display_lines.append(f"**🎞 Animation:** {s.get('animation_prompt', '')}")
        display_lines.append(f"**💬 Dialogue:**\n```\n{s.get('dialogue', '')}\n```")
        display_lines.append(f"**🔊 SFX:** {s.get('sound_effects', '')}")
        display_lines.append(f"**🎵 Music Mood:** {s.get('music_mood', '')} | "
                             f"**✂ Transition:** {s.get('transition', '')}")
        display_lines.append("")

    result = {
        "display_text": "\n".join(display_lines),
        "scenes": scenes,
    }
    cache_set("storyboard", cache_key, result)
    return result
