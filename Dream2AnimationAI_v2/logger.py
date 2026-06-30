"""
logger.py
─────────
Centralised logging for Dream2Animation AI.
All modules import `log` from here so output is consistent.
"""

import logging
import os
from config import LOGS_DIR

os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  │  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, "pipeline.log"), encoding="utf-8"),
    ],
)

log = logging.getLogger("Dream2AnimationAI")
