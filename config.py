"""Central configuration for DukaanDraft.

All settings are read from environment variables so the app stays local-first
and no secrets are stored in source control.
"""

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import os

# --- Ollama settings -------------------------------------------------------
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
# Generous default: the expanded schema needs more tokens, and the service
# allows one bounded retry on malformed output.
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "240"))

# --- Request handling ------------------------------------------------------
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", "8192"))

# --- Supported output languages --------------------------------------------
SUPPORTED_LANGUAGES = ["English", "Hindi", "Hinglish"]

# --- Product categories offered in the workspace ---------------------------
# The seller may still type a custom category — free text keeps working.
PRODUCT_CATEGORIES = [
    "Clothing & Fashion",
    "Footwear",
    "Jewellery & Accessories",
    "Beauty & Personal Care",
    "Home & Living",
    "Electronics",
    "Food & Other",
]

# --- Per-field input length limits -----------------------------------------
FIELD_LIMITS = {
    "product_name": 100,
    "category": 50,
    "price": 20,
    "features": 500,
    "target_audience": 200,
}
