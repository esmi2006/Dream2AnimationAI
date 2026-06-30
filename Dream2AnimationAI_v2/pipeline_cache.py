"""
cache.py
────────
Simple disk-based key/value cache.
Prevents duplicate Gemini / image calls if the pipeline is interrupted
and resumed, or if the user re-runs a step with the same inputs.

Usage
-----
    from pipeline_cache import cache_get, cache_set

    result = cache_get("story", prompt)
    if result is None:
        result = expensive_api_call(prompt)
        cache_set("story", prompt, result)
"""

import os
import json
import hashlib

# Lazy import to avoid circular import issues on startup
def _get_cache_dir():
    from config import CACHE_DIR
    os.makedirs(CACHE_DIR, exist_ok=True)
    return CACHE_DIR

def _log_info(msg):
    try:
        from logger import log
        log.info(msg)
    except Exception:
        print(msg)

def _log_warning(msg):
    try:
        from logger import log
        log.warning(msg)
    except Exception:
        print(msg)


def _key_path(namespace: str, key: str) -> str:
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return os.path.join(_get_cache_dir(), f"{namespace}_{digest}.json")


def cache_get(namespace: str, key: str):
    """Return cached value or None."""
    path = _key_path(namespace, key)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            _log_info(f"Cache hit  [{namespace}]")
            return data["value"]
        except Exception:
            pass
    return None


def cache_set(namespace: str, key: str, value) -> None:
    """Persist a value to disk cache."""
    path = _key_path(namespace, key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"value": value}, f, ensure_ascii=False, indent=2)
        _log_info(f"Cache set  [{namespace}]")
    except Exception as e:
        _log_warning(f"Cache write failed [{namespace}]: {e}")


def cache_clear(namespace: str | None = None) -> None:
    """Clear all cache entries, or only those for a given namespace."""
    cache_dir = _get_cache_dir()
    for fname in os.listdir(cache_dir):
        if namespace is None or fname.startswith(namespace):
            try:
                os.remove(os.path.join(cache_dir, fname))
            except Exception:
                pass
    _log_info(f"Cache cleared [namespace={namespace or 'ALL'}]")
