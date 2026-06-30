# 🎬 Dream2Animation AI — v2

Transform any story idea into a **cinematic animated movie** — automatically.

## Architecture

```
app.py                  ← Streamlit UI (pipeline orchestrator)
├── config.py           ← All settings & API keys
├── logger.py           ← Centralized logging
├── gemini_client.py    ← Shared Gemini client w/ retry
├── cache.py            ← Disk cache (resume support)
│
├── story_generator.py      → Full story (Act 1/2/3)
├── character_generator.py  → Character profiles + visual DNA
├── emotion_analyzer.py     → Emotional arc analysis
├── director_notes.py       → Cinematic director notes
├── storyboard_generator.py → 6-scene storyboard (JSON)
├── image_generator.py      → Cinematic scene images (16:9)
├── motion_generator.py     → Motion + camera plan
├── dialogue_generator.py   → Structured dialogue extraction
├── voice_generator.py      → Kokoro TTS per character
├── music_generator.py      → Background music (Pollinations)
└── movie_generator.py      → Final MP4 assembly (ffmpeg)
```

## Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install ffmpeg (required for movie assembly)
sudo apt install ffmpeg          # Ubuntu/Debian
brew install ffmpeg              # macOS

# 3. Set your Gemini API key
export GEMINI_API_KEY="your_key_here"
# or edit config.py

# 4. (Optional) Install Kokoro TTS for best voice quality
pip install kokoro-onnx

# 5. Run
streamlit run app.py
```

## Key Improvements vs v1

| Feature | v1 | v2 |
|---|---|---|
| Character consistency | ❌ No | ✅ Visual DNA injected into every image prompt |
| Image resolution | 1024×1024 (square) | 1280×720 (16:9 cinematic) |
| Storyboard richness | 5 fields | 12 fields (camera, SFX, music mood, etc.) |
| Data structure | Plain text | Structured JSON throughout |
| Caching | ❌ None | ✅ Disk cache — resume if interrupted |
| Voice per character | ❌ Same voice | ✅ Unique voice per character (gender/age aware) |
| Subtitle output | ❌ None | ✅ SRT file generated automatically |
| Movie assembly bugs | ✅ 5 bugs | ✅ All fixed |
| Logging | print() | Structured logging to file + console |
| Error handling | Minimal | Retry + graceful fallback everywhere |
| Scene count | Fixed 5 | Configurable 4-10 via UI slider |

## Pipeline Steps

1. **Story** — Pixar-style 3-act story with themes and moral
2. **Characters** — JSON profiles with visual DNA for consistency
3. **Emotion** — Emotional arc analysis (drives music selection)
4. **Director Notes** — Lighting, colour palette, camera style
5. **Storyboard** — 6 scenes with image prompts, dialogue, SFX, music mood
6. **Scene Images** — Cinematic 16:9 images (Pollinations Flux)
7. **Motion Plan** — Per-scene camera angles and character movement
8. **Dialogues** — Structured lines extracted from storyboard
9. **Voice** — Kokoro TTS per character (pyttsx3 fallback)
10. **Music** — Background music (Pollinations audio / procedural WAV)
11. **Movie** — Final MP4 with subtitles (ffmpeg)
