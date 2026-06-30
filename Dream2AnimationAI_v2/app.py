"""
app.py
──────
Dream2Animation AI — Streamlit UI

Full pipeline:
  Story → Characters → Emotion → Director Notes → Storyboard →
  Scene Images → Motion Plan → Dialogues → Voice → Music → Movie

Run:
    streamlit run app.py
"""

import os
import streamlit as st

from story_generator      import generate_story
from character_generator  import generate_characters
from emotion_analyzer     import analyze_emotion
from director_notes       import generate_director_notes
from storyboard_generator import generate_storyboard
from image_generator      import generate_scene_images
from motion_generator     import generate_motion
from dialogue_generator   import extract_dialogues
from voice_generator      import generate_voice
from config               import NUM_SCENES, MOVIE_PATH
from logger               import log

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dream2Animation AI",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 Dream2Animation AI")
st.caption("Transform any story idea into a cinematic animated movie — automatically.")

# ── Session state init ─────────────────────────────────────────────────────────
_STATE_KEYS = [
    "story", "characters", "emotion", "director_notes",
    "storyboard", "scene_images", "motion",
    "dialogues", "voice_result",
]
for k in _STATE_KEYS:
    if k not in st.session_state:
        st.session_state[k] = None

# ── Sidebar: pipeline status ──────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 Pipeline Status")
    status_map = {
        "✍ Story":           st.session_state.story,
        "👥 Characters":     st.session_state.characters,
        "😊 Emotion":        st.session_state.emotion,
        "🎬 Director Notes": st.session_state.director_notes,
        "🖼 Storyboard":     st.session_state.storyboard,
        "🎞 Scene Images":   st.session_state.scene_images,
        "🎥 Motion Plan":    st.session_state.motion,
        "💬 Dialogues":      st.session_state.dialogues,
        "🔊 Voice":          st.session_state.voice_result,
    }
    for label, val in status_map.items():
        icon = "✅" if val else "⏳"
        st.write(f"{icon} {label}")

    st.divider()
    st.subheader("⚙ Settings")
    num_scenes = st.slider("Number of Scenes", 4, 10, NUM_SCENES)

    if st.button("🗑 Clear All Cache"):
        from pipeline_cache import cache_clear
        cache_clear()
        st.success("Cache cleared.")

# ── Input section ─────────────────────────────────────────────────────────────
with st.container():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        idea = st.text_input("💡 Story Idea", placeholder="A young firefly who can't glow...")
    with col2:
        genre = st.selectbox("Genre", ["Adventure", "Comedy", "Fantasy", "Horror",
                                        "Sci-Fi", "Drama", "Romance"])
    with col3:
        audience = st.selectbox("Audience", ["Kids", "Teens", "Adults", "Family"])
    with col4:
        language = st.selectbox("Language", ["English", "Tamil", "Hindi", "Spanish", "French"])

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — STORY, CHARACTERS, EMOTION, DIRECTOR, STORYBOARD, IMAGES
# ══════════════════════════════════════════════════════════════════════════════
if st.button("🚀 Generate Full Story Pipeline", type="primary"):
    if not idea.strip():
        st.warning("Please enter a story idea.")
        st.stop()

    log.info(f"Starting pipeline: idea='{idea}' genre={genre} audience={audience}")

    # ── Story ─────────────────────────────────────────────────────────────────
    with st.spinner("✍ Writing story..."):
        st.session_state.story = generate_story(idea, genre, audience, language)
    with st.expander("📖 Story", expanded=True):
        if st.session_state.story:
            st.markdown(st.session_state.story)
        else:
            st.error("❌ Story generation returned empty. Your Gemini API key is likely invalid or missing.")
            st.info("Fix: Open `config.py` and set `GEMINI_API_KEY = \"AIzaSy...\"` (get a free key at https://aistudio.google.com/app/apikey)")
            st.stop()

    # ── Characters ────────────────────────────────────────────────────────────
    with st.spinner("👥 Designing characters..."):
        char_result = generate_characters(st.session_state.story)
        st.session_state.characters = char_result
    with st.expander("👥 Character Profiles"):
        st.markdown(char_result["profiles_text"])

    characters = char_result.get("characters", [])

    # ── Emotion ───────────────────────────────────────────────────────────────
    with st.spinner("😊 Analyzing emotion..."):
        st.session_state.emotion = analyze_emotion(st.session_state.story)
    with st.expander("😊 Emotion Analysis"):
        st.markdown(st.session_state.emotion)

    # ── Director Notes ────────────────────────────────────────────────────────
    with st.spinner("🎬 Generating director notes..."):
        st.session_state.director_notes = generate_director_notes(st.session_state.story)
    with st.expander("🎬 Director Notes"):
        st.markdown(st.session_state.director_notes)

    # ── Storyboard ────────────────────────────────────────────────────────────
    with st.spinner("🖼 Building storyboard..."):
        sb = generate_storyboard(st.session_state.story, characters, num_scenes)
        st.session_state.storyboard = sb
    with st.expander("🖼 Storyboard", expanded=True):
        st.markdown(sb["display_text"])

    scenes = sb.get("scenes", [])

    # ── Scene Images ──────────────────────────────────────────────────────────
    with st.spinner("🎞 Generating cinematic scene images (this takes a moment)..."):
        image_paths = generate_scene_images(scenes, characters)
        st.session_state.scene_images = image_paths

    st.subheader("🎞 Scene Images")
    if not image_paths:
        st.error("No scene images generated.")
    else:
        cols = st.columns(min(3, len(image_paths)))
        for i, img_path in enumerate(image_paths):
            with cols[i % len(cols)]:
                scene_title = scenes[i].get("title", f"Scene {i+1}") if i < len(scenes) else f"Scene {i+1}"
                st.image(img_path, caption=f"Scene {i+1}: {scene_title}",
                         use_container_width=True)

    st.success(f"✅ Story pipeline complete! {len(image_paths)} scenes generated.")
    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — MOTION & CAMERA
# ══════════════════════════════════════════════════════════════════════════════
_scenes_ready = (
    st.session_state.storyboard
    and isinstance(st.session_state.storyboard, dict)
    and len(st.session_state.storyboard.get("scenes", [])) > 0
)

if _scenes_ready:
    if st.button("🎥 Generate Motion & Camera Plan"):
        scenes = st.session_state.storyboard["scenes"]
        with st.spinner("Planning motion and camera..."):
            st.session_state.motion = generate_motion(scenes)
        with st.expander("🎥 Motion & Camera Plan", expanded=True):
            st.markdown(st.session_state.motion["display_text"])
        st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — DIALOGUES
# ══════════════════════════════════════════════════════════════════════════════
if _scenes_ready:
    if st.button("💬 Extract Dialogues"):
        scenes = st.session_state.storyboard["scenes"]
        with st.spinner("Extracting dialogue lines..."):
            st.session_state.dialogues = extract_dialogues(scenes)
        with st.expander("💬 Movie Script", expanded=True):
            st.markdown(st.session_state.dialogues["script_text"])
        st.info(f"📝 {len(st.session_state.dialogues['lines'])} dialogue lines extracted.")
        st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — VOICE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.dialogues and st.session_state.characters:
    if st.button("🔊 Generate Character Voices"):
        dialogue_lines = st.session_state.dialogues["lines"]
        characters     = st.session_state.characters.get("characters", [])

        with st.spinner("Generating character voices (Kokoro TTS)..."):
            result = generate_voice(dialogue_lines, characters)
            st.session_state.voice_result = result

        st.header("🔊 Character Voices")

        if result.get("voice_map"):
            st.subheader("🎭 Voice Assignments")
            rows = [{"Character": k, "Voice ID": v}
                    for k, v in result["voice_map"].items()]
            st.table(rows)

        if result.get("line_files"):
            st.subheader("🎙 Individual Lines")
            for i, (path, meta) in enumerate(
                zip(result["line_files"], result.get("line_metadata", [])), 1
            ):
                if os.path.exists(path):
                    label = (f"Line {i} — {meta.get('character', '?')}: "
                             f"{meta.get('text', '')[:60]}")
                    st.caption(label)
                    st.audio(path)

        if result.get("movie_voice") and os.path.exists(result["movie_voice"]):
            st.subheader("🎬 Merged Voice Track")
            st.audio(result["movie_voice"])
            st.success(f"✅ movie_voice.wav ready")
        else:
            st.warning("Voice merge failed. Check Kokoro/pyttsx3 installation.")
        st.divider()

