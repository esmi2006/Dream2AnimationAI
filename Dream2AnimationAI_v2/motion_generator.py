"""
motion_generator.py
───────────────────
Generates a detailed motion plan and camera direction for every scene.
Returns both display markdown and a structured list for the animation pipeline.

Public API
----------
    generate_motion(scenes: list) -> dict
        {
          "display_text": str,
          "motion_plans": [
            {
              "scene_number": int,
              "character_movement": str,
              "facial_expression": str,
              "background_animation": str,
              "lighting_animation": str,
              "special_effects": str,
              "animation_duration": str,
              "camera_shot": str,
              "camera_angle": str,
              "camera_movement": str,
              "lens": str,
              "focus": str,
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


_PROMPT = """
You are a Senior Pixar Animation Director and DOP.

Generate a complete motion and camera plan for each scene below.

Return ONLY a valid JSON array — no markdown, no fences.

[
  {{
    "scene_number": 1,
    "character_movement": "Detailed body movement — 15-20 words",
    "facial_expression": "Key expressions per character — 10-15 words",
    "background_animation": "Environmental motion — 10-15 words",
    "lighting_animation": "Dynamic lighting changes during the scene — 10 words",
    "special_effects": "Particle effects, magic, weather etc — 10 words or 'none'",
    "animation_duration": "6",
    "camera_shot": "Wide Shot | Medium Shot | Close-up | Extreme Close-up | Overhead | Two-Shot",
    "camera_angle": "Eye Level | Low Angle | High Angle | Dutch Angle | Bird's Eye",
    "camera_movement": "Static | Pan Left | Pan Right | Tilt Up | Tilt Down | Dolly In | Dolly Out | Crane Up | Orbit | Handheld Shake | Tracking",
    "lens": "24mm | 35mm | 50mm | 85mm | 135mm",
    "focus": "Deep Focus | Rack Focus | Shallow DOF",
    "transition": "Cut | Fade In | Fade Out | Dissolve | Wipe | Smash Cut"
  }}
]

Rules:
• One object per scene, in order.
• Camera shot, angle, and movement must vary — no repeating the same combo twice in a row.
• Choose movements that serve the emotional beat of each scene.
• animation_duration is a number string (seconds).

Scenes (JSON):
{scenes_json}
"""


def generate_motion(scenes: list) -> dict:
    if not scenes:
        return {"display_text": "⚠ No scenes available. Run the Story Pipeline first.", "motion_plans": []}
    """
    Generate motion and camera plan for all scenes.

    Parameters
    ----------
    scenes : list of scene dicts from storyboard_generator

    Returns
    -------
    dict with "display_text" and "motion_plans"
    """
    cache_key = str(len(scenes)) + str(scenes[0].get("title", ""))[:30]
    cached = cache_get("motion", cache_key)
    if cached:
        return cached

    log.info("Generating motion & camera plan...")
    slim = [{"scene_number": s.get("scene_number"),
             "title": s.get("title"),
             "character_actions": s.get("character_actions"),
             "music_mood": s.get("music_mood")} for s in scenes]
    import json as _json
    prompt = _PROMPT.format(scenes_json=_json.dumps(slim, indent=2))

    # Use main model (not fast=True) for reliability
    raw = ask(prompt, fast=False)
    raw = re.sub(r"```(?:json)?|```", "", raw).strip()
    log.info(f"Motion raw response: {len(raw)} chars")

    motion_plans = []
    if not raw:
        log.error("Motion plan: Gemini returned empty.")
        return {
            "display_text": "❌ Gemini returned empty for motion plan. Check your API key and model name in config.py.",
            "motion_plans": []
        }

    try:
        motion_plans = json.loads(raw)
    except Exception as e:
        log.warning(f"Motion JSON parse error: {e}")
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                motion_plans = json.loads(match.group(0))
            except Exception:
                pass
        if not motion_plans:
            return {
                "display_text": f"❌ Motion plan JSON parse failed.\n\nRaw response:\n```\n{raw[:500]}\n```",
                "motion_plans": []
            }

    # Build display markdown
    lines = ["# 🎥 Motion & Camera Plan\n"]
    for mp in motion_plans:
        n = mp.get("scene_number", "?")
        lines.append(f"---\n## Scene {n}")
        lines.append(f"**🏃 Movement:** {mp.get('character_movement', '')}")
        lines.append(f"**😊 Expressions:** {mp.get('facial_expression', '')}")
        lines.append(f"**🌿 Background:** {mp.get('background_animation', '')}")
        lines.append(f"**💡 Lighting:** {mp.get('lighting_animation', '')}")
        lines.append(f"**✨ FX:** {mp.get('special_effects', '')}")
        lines.append(f"**⏱ Duration:** {mp.get('animation_duration', '')}s")
        lines.append(f"**📷 Shot:** {mp.get('camera_shot', '')} | "
                     f"**Angle:** {mp.get('camera_angle', '')} | "
                     f"**Move:** {mp.get('camera_movement', '')}")
        lines.append(f"**🔭 Lens:** {mp.get('lens', '')} | "
                     f"**Focus:** {mp.get('focus', '')} | "
                     f"**Cut:** {mp.get('transition', '')}")
        lines.append("")

    result = {"display_text": "\n".join(lines), "motion_plans": motion_plans}
    cache_set("motion", cache_key, result)
    return result
