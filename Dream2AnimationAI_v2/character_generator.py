"""
character_generator.py
──────────────────────
Generates rich character profiles AND a "visual DNA" block for each character.

The visual DNA is the canonical set of appearance descriptors that gets
injected into every image prompt to guarantee cross-scene consistency.

Public API
----------
    generate_characters(story: str) -> dict
        Returns:
            {
              "profiles_text": str,         # markdown for display
              "characters": [               # structured list
                {
                  "name": str,
                  "role": str,
                  "gender": str,
                  "age": str,
                  "voice_gender": str,      # "male" | "female" | "neutral"
                  "voice_age": str,         # "child" | "young" | "adult" | "elder"
                  "personality": str,
                  "visual_dna": str,        # 40-60 word appearance block for image prompts
                  "tts_voice": str,         # suggested Kokoro voice ID
                }
              ]
            }
"""

import json
import re
from gemini_client import ask
from pipeline_cache import cache_get, cache_set
from logger import log


_PROFILE_PROMPT = """
You are a professional character designer for a Pixar/DreamWorks animated movie.

Read the story carefully and identify ALL main and supporting characters.

For EACH character, output a JSON object in this EXACT structure.
Return ONLY a valid JSON array — no markdown fences, no extra text.

[
  {{
    "name": "Character Name",
    "role": "protagonist | antagonist | supporting",
    "gender": "male | female | non-binary",
    "age": "numeric age or range, e.g. 10 or 30-35",
    "voice_gender": "male | female | neutral",
    "voice_age": "child | young | adult | elder",
    "personality": "3-5 key traits, comma-separated",
    "appearance": {{
      "body": "height, build, posture — 10 words max",
      "face": "face shape, eye color, expression — 10 words max",
      "hair": "color, length, style — 8 words max",
      "skin_tone": "specific tone, e.g. warm olive, deep brown, pale porcelain",
      "clothes": "outfit description — 15 words max",
      "accessories": "any hats, glasses, tools, etc. — 8 words max or 'none'"
    }},
    "tts_voice": "af_sky | am_adam | af_bella | am_michael | af_nicole | am_onyx"
  }}
]

Voice assignment rules:
- female child/young → af_sky or af_bella
- female adult → af_nicole or af_bella
- male child/young → am_adam
- male adult/elder → am_michael or am_onyx
- neutral/non-binary → af_sky

Story:
{story}
"""


def _build_visual_dna(char: dict) -> str:
    """
    Compress appearance fields into a single, reusable prompt fragment.
    This gets prepended to every scene image prompt for this character.
    """
    a = char.get("appearance", {})
    parts = [
        char.get("name", ""),
        f"{char.get('age', '')} year old {char.get('gender', '')}",
        a.get("body", ""),
        a.get("face", ""),
        a.get("hair", ""),
        f"skin tone: {a.get('skin_tone', '')}",
        f"wearing {a.get('clothes', '')}",
    ]
    if a.get("accessories") and a["accessories"].lower() != "none":
        parts.append(a["accessories"])
    dna = ", ".join(p for p in parts if p.strip())
    return dna


def generate_characters(story: str) -> dict:
    """
    Parse story and return character profiles + visual DNA.
    """
    cached = cache_get("characters", story[:200])
    if cached:
        return cached

    log.info("Generating character profiles...")
    prompt = _PROFILE_PROMPT.format(story=story)
    raw = ask(prompt)

    # Strip markdown fences if Gemini added them anyway
    raw = re.sub(r"```(?:json)?|```", "", raw).strip()

    characters = []
    try:
        parsed = json.loads(raw)
        for char in parsed:
            char["visual_dna"] = _build_visual_dna(char)
            characters.append(char)
    except json.JSONDecodeError as e:
        log.warning(f"Character JSON parse failed: {e}. Returning raw text only.")

    # Build markdown display text
    lines = ["# 👥 Character Profiles\n"]
    for c in characters:
        lines.append(f"## {c.get('name', 'Unknown')}")
        lines.append(f"- **Role:** {c.get('role', '')}")
        lines.append(f"- **Age / Gender:** {c.get('age', '')} / {c.get('gender', '')}")
        lines.append(f"- **Personality:** {c.get('personality', '')}")
        a = c.get("appearance", {})
        lines.append(f"- **Appearance:** {a.get('face', '')}; {a.get('hair', '')}; "
                     f"skin {a.get('skin_tone', '')}; {a.get('clothes', '')}")
        lines.append(f"- **Visual DNA:** `{c.get('visual_dna', '')}`")
        lines.append(f"- **TTS Voice:** `{c.get('tts_voice', '')}`")
        lines.append("")

    result = {
        "profiles_text": "\n".join(lines),
        "characters": characters,
    }
    cache_set("characters", story[:200], result)
    return result
