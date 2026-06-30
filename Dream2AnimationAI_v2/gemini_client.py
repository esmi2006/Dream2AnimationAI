"""
gemini_client.py
────────────────
Single shared Gemini client with retry logic and rate-limit handling.
All modules should call `ask()` rather than creating their own model instances.
"""

import time
import google as genai
from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, GEMINI_FAST_MODEL
from logger import log

genai.configure(api_key=GEMINI_API_KEY)
print("API KEY:",GEMINI_API_KEY[:10])
print("MODEL:",GEMINI_TEXT_MODEL)

_text_model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
_fast_model = genai.GenerativeModel(GEMINI_FAST_MODEL)


def ask(prompt: str, fast: bool = False, retries: int = 3) -> str:
    """
    Send a prompt to Gemini and return the response text.

    Parameters
    ----------
    prompt  : the full prompt string
    fast    : use the faster/cheaper model (gemini-2.0-flash)
    retries : number of retry attempts on transient errors
    """
    model = _fast_model if fast else _text_model
    for attempt in range(1, retries + 1):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            log.warning(f"Gemini attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)   # exponential back-off
    log.error("Gemini: all retries exhausted.")
    return ""
