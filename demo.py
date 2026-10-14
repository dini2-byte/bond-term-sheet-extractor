"""Upload size check and Gemini key lookup for the page."""

import os
from typing import Any

MAX_UPLOAD_SIZE_BYTES = 500 * 1024  # 500 KB limit


def check_upload_size(size_bytes: int, max_bytes: int = MAX_UPLOAD_SIZE_BYTES) -> tuple[bool, str | None]:
    """Check whether uploaded file size is within the allowed threshold (500 KB)."""
    if size_bytes > max_bytes:
        limit_kb = max_bytes // 1024
        actual_kb = size_bytes / 1024
        return False, f"Upload rejected: file size ({actual_kb:.1f} KB) exceeds the {limit_kb} KB limit."
    return True, None


def get_gemini_api_key(secrets: dict[str, Any] | None = None) -> str | None:
    """
    Retrieve Gemini API key from Streamlit secrets first, then environment.
    Never prints or logs the key.
    """
    if secrets:
        key = secrets.get("GEMINI_API_KEY")
        if key and isinstance(key, str) and key.strip():
            return key.strip()

    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    return None
