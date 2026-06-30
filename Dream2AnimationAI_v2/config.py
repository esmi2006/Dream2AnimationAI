"""
config.py
─────────
Central configuration for Dream2Animation AI.
All API keys and tuneable constants live here.
"""

import os

# ── API Keys ──────────────────────────────────────────────────────────────────
# Set via environment variables for security, or replace the defaults here.
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")

# ── Model names ───────────────────────────────────────────────────────────────
GEMINI_TEXT_MODEL  = "gemini-2.5-flash"   # story, storyboard, characters, dialogue
GEMINI_FAST_MODEL  = "gemini-2.5-flash"   # emotion, director notes, music profile

# ── Image generation (Pollinations – free, no key) ───────────────────────────
IMAGE_MODEL        = "flux"
IMAGE_WIDTH        = 1280
IMAGE_HEIGHT       = 720    # 16:9 cinematic aspect ratio
IMAGE_ENHANCE      = True

# ── Pipeline settings ─────────────────────────────────────────────────────────
NUM_SCENES         = 6      # number of storyboard scenes
SCENE_DURATION_S   = 7.0   # fallback seconds per scene when no voice
MIN_SCENE_DURATION = 5.0   # minimum seconds per scene

# ── Voice (Kokoro TTS) ────────────────────────────────────────────────────────
VOICES_DIR         = "voices"

# ── Output paths ─────────────────────────────────────────────────────────────
SCENES_DIR         = "scenes"
CACHE_DIR          = "cache"
LOGS_DIR           = "logs"
EXPORTS_DIR        = "exports"
MUSIC_PATH         = "background_music.wav"
MOVIE_PATH         = "exports/final_animation.mp4"

# ── Movie output ──────────────────────────────────────────────────────────────
VIDEO_FPS          = 24
VIDEO_RESOLUTION   = "1280:720"
MUSIC_VOLUME       = 0.20   # background music vs dialogue volume ratio


