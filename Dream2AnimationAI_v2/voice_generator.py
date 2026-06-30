"""
voice_generator.py
──────────────────
Generates character voices using Kokoro TTS (local, free).

Key behaviour
-------------
• Every character automatically gets a voice based on Gender, Age and Role
  — no character names are ever hardcoded.
• The same character name always resolves to the same voice, both within
  a run and across re-runs (deterministic hashing + on-disk cache), so a
  character keeps an identical voice in every scene.
• Dialogue audio is generated scene by scene, one separate WAV file per
  dialogue line.
• The Kokoro `KPipeline` is created ONCE per language and reused for every
  line (previously it was re-created per line, which was the main source
  of slow generation times).
• Existing WAV files are never regenerated — duplicate voice generation is
  skipped automatically.
• Voice assignments are cached to disk via pipeline_cache so repeated runs
  with the same character set don't recompute anything.

Public API
----------
    generate_voice(dialogue_lines, characters) -> dict
        {
          "voice_map": {character_name: voice_id, ...},
          "line_files": [path, ...],
          "line_metadata": [{line_index, scene_number, character, text,
                              path, duration_s}, ...],
          "movie_voice": "voices/movie_voice.wav" | None,
        }
"""

import os
import wave
import struct
import pyttsx3
import hashlib
from config import VOICES_DIR
from logger import log

try:
    from pipeline_cache import cache_get, cache_set
except Exception:  # pragma: no cover - cache is optional, never fatal
    def cache_get(*_a, **_k):
        return None

    def cache_set(*_a, **_k):
        return None

os.makedirs(VOICES_DIR, exist_ok=True)

# ── Voice pool ──────────────────────────────────────────────────────────────
# Several Kokoro voice IDs per (gender, age) bucket so that different
# characters who share a gender/age combo don't all sound identical.
# Role is used to bias which voice in the bucket is picked (e.g. an
# antagonist tends to get a different voice than the protagonist even if
# both are "male_adult").
_VOICE_BUCKETS = {
    ("female", "child"):  ["af_sky", "af_bella"],
    ("female", "young"):  ["af_bella", "af_sky", "af_nicole"],
    ("female", "adult"):  ["af_nicole", "af_bella", "af_sky"],
    ("female", "elder"):  ["af_nicole", "af_sky"],
    ("male",   "child"):  ["am_adam"],
    ("male",   "young"):  ["am_adam", "am_michael"],
    ("male",   "adult"):  ["am_michael", "am_onyx", "am_adam"],
    ("male",   "elder"):  ["am_onyx", "am_michael"],
    ("neutral", "child"): ["af_sky"],
    ("neutral", "young"): ["af_sky", "am_adam"],
    ("neutral", "adult"): ["af_nicole", "am_michael"],
    ("neutral", "elder"): ["am_onyx", "af_nicole"],
}
_DEFAULT_VOICE = "af_sky"

# Silence gap between merged lines (seconds)
_LINE_GAP_S = 0.6

# Reused Kokoro pipeline instances, keyed by lang_code, so we never pay the
# (expensive) model-load cost more than once per process.
_KOKORO_PIPELINES: dict = {}


def _normalise_age(age) -> str:
    """Map a free-form age value ('10', '30-35', 'elder', etc.) to a bucket."""
    if age is None:
        return "adult"
    age_str = str(age).lower().strip()
    if any(w in age_str for w in ("child", "kid", "young boy", "young girl")):
        return "child"
    if any(w in age_str for w in ("elder", "old", "senior")):
        return "elder"
    if any(w in age_str for w in ("teen", "young", "youth")):
        return "young"
    # Try to pull a numeric value out of things like "30-35" or "12"
    digits = "".join(c if c.isdigit() else " " for c in age_str).split()
    if digits:
        try:
            num = int(digits[0])
            if num <= 12:
                return "child"
            if num <= 19:
                return "young"
            if num >= 60:
                return "elder"
            return "adult"
        except ValueError:
            pass
    return "adult"


def _normalise_gender(gender) -> str:
    g = str(gender or "neutral").lower().strip()
    if "fem" in g or g.startswith("f"):
        return "female"
    if "mal" in g or g.startswith("m"):
        return "male"
    return "neutral"


def _stable_choice(options: list, seed: str):
    """Deterministically pick one item from `options` based on `seed`."""
    if not options:
        return _DEFAULT_VOICE
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    idx = int(digest, 16) % len(options)
    return options[idx]


def _assign_voices(characters: list) -> dict:
    """
    Map character name → Kokoro voice ID, using Gender + Age + Role.
    No character names are hardcoded; everything is derived dynamically
    from the character profile produced by character_generator.
    """
    voice_map = {}
    for char in characters:
        name = char.get("name", "Unknown")

        # Respect an explicit tts_voice from the character profile when present
        # (character_generator already derives this from gender/age/role).
        explicit = char.get("tts_voice")

        gender = _normalise_gender(char.get("voice_gender") or char.get("gender"))
        age = _normalise_age(char.get("voice_age") or char.get("age"))
        role = str(char.get("role", "supporting")).lower().strip()

        bucket = _VOICE_BUCKETS.get((gender, age), [_DEFAULT_VOICE])

        if explicit and explicit in {v for vs in _VOICE_BUCKETS.values() for v in vs}:
            voice_id = explicit
        else:
            # Deterministic per-character pick within the bucket, seeded by
            # name + role so the same character always gets the same voice,
            # while different characters in the same bucket tend to diverge.
            voice_id = _stable_choice(bucket, seed=f"{name}|{role}|{gender}|{age}")

        voice_map[name] = voice_id

    log.info(f"Voice map: {voice_map}")
    return voice_map


def _characters_signature(characters: list) -> str:
    """Build a stable cache key from the character set (name/role/gender/age)."""
    parts = sorted(
        f"{c.get('name','')}:{c.get('role','')}:"
        f"{c.get('voice_gender', c.get('gender',''))}:"
        f"{c.get('voice_age', c.get('age',''))}"
        for c in characters
    )
    return "|".join(parts)


def _kokoro_available() -> bool:
    try:
        import kokoro  # noqa: F401
        return True
    except ImportError:
        return False


def _get_kokoro_pipeline(lang_code: str = "a"):
    """Return a cached KPipeline instance, creating it only once per process."""
    if lang_code not in _KOKORO_PIPELINES:
        from kokoro import KPipeline
        log.info(f"Loading Kokoro pipeline (lang_code='{lang_code}')...")
        _KOKORO_PIPELINES[lang_code] = KPipeline(lang_code=lang_code)
    return _KOKORO_PIPELINES[lang_code]


def _generate_line_kokoro(text: str, voice_id: str, output_path: str) -> bool:
    """Generate a single WAV line using the shared Kokoro TTS pipeline."""
    try:
        import soundfile as sf
        import numpy as np

        pipeline = _get_kokoro_pipeline("a")  # 'a' = American English
        generator = pipeline(text, voice=voice_id, speed=0.95, split_pattern=r"\n+")
        samples = []
        sample_rate = 24000
        for _gs, _ps, audio in generator:
            samples.append(audio)
        if samples:
            audio_np = np.concatenate(samples)
            sf.write(output_path, audio_np, sample_rate)
            return True
    except Exception as e:
        log.warning(f"Kokoro TTS error: {e}")
    return False


def _generate_line_pyttsx3(text: str, output_path: str) -> bool:
    """Fallback TTS using pyttsx3 (system voices)."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 160)
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        return os.path.exists(output_path) and os.path.getsize(output_path) > 100
    except Exception as e:
        log.warning(f"pyttsx3 TTS error: {e}")
    return False


def _generate_line_silent(text: str, output_path: str) -> bool:
    """
    Last-resort: write a silent WAV whose duration approximates speech timing.
    Roughly 130 words per minute.
    """
    word_count = len(text.split())
    duration_s = max(1.5, word_count / 130 * 60)
    sample_rate = 24000
    num_samples = int(sample_rate * duration_s)
    try:
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack("<" + "h" * num_samples, *([0] * num_samples)))
        return True
    except Exception as e:
        log.error(f"Silent WAV failed: {e}")
    return False


def _wav_duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as wf:
            return wf.getnframes() / wf.getframerate()
    except Exception:
        return 0.0


def _merge_wav_files(wav_paths: list, output_path: str,
                     gap_s: float = _LINE_GAP_S) -> bool:
    """
    Concatenate WAV files with a silence gap between each.
    All files must be mono 24 kHz 16-bit.
    """
    sample_rate = 24000
    gap_samples = int(sample_rate * gap_s)
    silence_block = struct.pack("<" + "h" * gap_samples, *([0] * gap_samples))

    all_frames = bytearray()
    for path in wav_paths:
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                all_frames.extend(frames)
            all_frames.extend(silence_block)
        except Exception as e:
            log.warning(f"Could not read {path}: {e}")

    if not all_frames:
        return False

    try:
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(bytes(all_frames))
        return True
    except Exception as e:
        log.error(f"WAV merge failed: {e}")
        return False


def generate_voice(dialogue_lines: list, characters: list) -> dict:
    """
    Generate voice for every dialogue line, scene by scene.

    Parameters
    ----------
    dialogue_lines : list of {line_index, scene_number, character, text}
                      (already ordered scene by scene by dialogue_generator)
    characters     : list of character dicts from character_generator

    Returns
    -------
    dict with voice_map, line_files, line_metadata, movie_voice
    """
    # ── Voice assignment (cached so repeated runs with the same cast skip
    #    recomputation entirely) ─────────────────────────────────────────
    sig = _characters_signature(characters)
    voice_map = cache_get("voice_map", sig) if sig else None
    if voice_map is None:
        voice_map = _assign_voices(characters)
        if sig:
            cache_set("voice_map", sig, voice_map)
    else:
        log.info(f"Voice map (cached): {voice_map}")

    use_kokoro = _kokoro_available()
    log.info(f"TTS engine: {'Kokoro' if use_kokoro else 'pyttsx3 / silent fallback'}")

    line_files = []
    line_metadata = []

    # Group lines by scene so generation proceeds scene by scene, in order.
    lines_by_scene: dict = {}
    for line in dialogue_lines:
        lines_by_scene.setdefault(line["scene_number"], []).append(line)

    for scene_number in sorted(lines_by_scene.keys()):
        scene_lines = lines_by_scene[scene_number]
        log.info(f"🎬 Generating voices for scene {scene_number} "
                 f"({len(scene_lines)} line(s))...")

        for line in scene_lines:
            i = line["line_index"]
            char = line["character"]
            text = line["text"]
            voice_id = voice_map.get(char, _DEFAULT_VOICE)

            wav_path = os.path.join(VOICES_DIR, f"line_{i}.wav")

            # Skip if already exists (avoids duplicate generation / resume support)
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
                log.info(f"Line {i}: already cached on disk, skipping.")
            else:
                success = False
                if use_kokoro:
                    success = _generate_line_kokoro(text, voice_id, wav_path)
                if not success:
                    success = _generate_line_pyttsx3(text, wav_path)
                if not success:
                    _generate_line_silent(text, wav_path)
                    log.warning(f"Line {i}: using silent placeholder.")

            duration = _wav_duration(wav_path) if os.path.exists(wav_path) else 0.0
            line_files.append(wav_path)
            line_metadata.append({
                "line_index": i,
                "scene_number": scene_number,
                "character": char,
                "text": text,
                "path": wav_path,
                "duration_s": duration,
            })
            log.info(f"Line {i} ({char}, voice={voice_id}): "
                     f"{duration:.1f}s — {text[:50]}")

    # Merge all lines into movie_voice.wav
    movie_voice_path = os.path.join(VOICES_DIR, "movie_voice.wav")
    merged = _merge_wav_files(line_files, movie_voice_path)
    movie_voice = movie_voice_path if merged else None
    if merged:
        total_dur = _wav_duration(movie_voice_path)
        log.info(f"✅ movie_voice.wav → {total_dur:.1f}s total")
    else:
        log.warning("Could not merge voice lines.")

    return {
        "voice_map": voice_map,
        "line_files": line_files,
        "line_metadata": line_metadata,
        "movie_voice": movie_voice,
    }
