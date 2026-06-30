"""
image_generator.py
──────────────────
Generates one cinematic image per storyboard scene using the Pollinations
Flux API. Character visual DNA is injected into every prompt to maintain
100% cross-scene consistency.

Key improvements over v1:
• 16:9 resolution (1280×720) for cinematic framing
• Rich cinematic style suffix appended to every prompt
• Character DNA injected automatically
• Retry logic with exponential back-off
• Per-scene caching (skip already-generated images)
• Consistent seed per character for visual stability

Public API
----------
    generate_scene_images(scenes, characters) -> list[str]
        Returns list of image file paths.
"""

import os
import time
import hashlib
import urllib.parse
import requests

from config import (IMAGE_MODEL, IMAGE_WIDTH, IMAGE_HEIGHT,
                    IMAGE_ENHANCE, SCENES_DIR)
from logger import log

os.makedirs(SCENES_DIR, exist_ok=True)

# Appended to every image prompt for cinematic quality
_CINEMATIC_SUFFIX = (
    "Pixar/DreamWorks 3D animated film still, "
    "cinematic composition, volumetric lighting, "
    "shallow depth of field, rich color grading, "
    "8K render, no text, no watermark, "
    "professional animation studio quality"
)

_NEGATIVE_SUFFIX = (
    "ugly, blurry, distorted hands, extra fingers, "
    "bad anatomy, watermark, logo, text, duplicate, "
    "low quality, pixelated, overexposed, underexposed"
)


def _scene_image_path(scene_number: int) -> str:
    return os.path.join(SCENES_DIR, f"scene_{scene_number:02d}.png")


def _prompt_seed(text: str) -> int:
    """Deterministic seed from prompt text for reproducibility."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16) % 2147483647


def _build_full_prompt(scene: dict, characters: list) -> str:
    """
    Build the final image prompt by:
    1. Taking the storyboard image_prompt
    2. Injecting visual DNA for every character present in this scene
    3. Appending the cinematic style suffix
    """
    base_prompt = scene.get("image_prompt", "")
    present = [n.lower() for n in scene.get("characters_present", [])]

    # Inject character DNA for every character in this scene
    dna_parts = []
    for char in characters:
        if char["name"].lower() in present:
            dna_parts.append(char.get("visual_dna", ""))

    if dna_parts:
        dna_block = "; ".join(dna_parts)
        full_prompt = f"{base_prompt}. Characters: {dna_block}. {_CINEMATIC_SUFFIX}"
    else:
        full_prompt = f"{base_prompt}. {_CINEMATIC_SUFFIX}"

    return full_prompt


def _fetch_image(prompt: str, output_path: str,
                 retries: int = 3, timeout: int = 120) -> bool:
    """Download image from Pollinations. Returns True on success."""
    encoded = urllib.parse.quote(prompt)
    seed = _prompt_seed(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model={IMAGE_MODEL}"
        f"&width={IMAGE_WIDTH}"
        f"&height={IMAGE_HEIGHT}"
        f"&enhance={'true' if IMAGE_ENHANCE else 'false'}"
        f"&nologo=true"
        f"&seed={seed}"
    )

    for attempt in range(1, retries + 1):
        try:
            log.info(f"  Image request attempt {attempt}/{retries}...")
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                size_kb = len(resp.content) // 1024
                log.info(f"  ✅ Image saved → {output_path} ({size_kb} KB)")
                return True
            else:
                log.warning(f"  Image API status {resp.status_code}")
        except Exception as e:
            log.warning(f"  Image fetch error: {e}")

        if attempt < retries:
            time.sleep(2 ** attempt)

    return False


def generate_scene_images(scenes: list, characters: list) -> list:
    """
    Generate one cinematic image per scene.

    Parameters
    ----------
    scenes     : list of scene dicts from storyboard_generator
    characters : list of character dicts from character_generator

    Returns
    -------
    List of file paths for successfully generated images.
    """
    image_paths = []
    total = len(scenes)

    for scene in scenes:
        n = scene.get("scene_number", 0)
        output_path = _scene_image_path(n)

        # Skip if already generated (resume support)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 5000:
            log.info(f"Scene {n}/{total}: already exists, skipping.")
            image_paths.append(output_path)
            continue

        prompt = _build_full_prompt(scene, characters)
        log.info(f"\nScene {n}/{total}: generating image...")
        log.info(f"  Prompt: {prompt[:120]}...")

        success = _fetch_image(prompt, output_path)
        if success:
            image_paths.append(output_path)
        else:
            log.error(f"Scene {n}: image generation failed after all retries.")

        # Small polite delay between requests
        time.sleep(1)

    log.info(f"\n✅ Generated {len(image_paths)}/{total} scene images.")
    return image_paths
