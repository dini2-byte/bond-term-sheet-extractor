from pathlib import Path

from demo import (
    MAX_UPLOAD_SIZE_BYTES,
    check_upload_size,
    get_gemini_api_key,
)


class TestUploadSizeAndApiKey:
    def test_check_upload_size_within_limit(self):
        ok, msg = check_upload_size(400 * 1024)
        assert ok is True
        assert msg is None

    def test_check_upload_size_exact_boundary(self):
        ok, msg = check_upload_size(500 * 1024)
        assert ok is True
        assert msg is None

    def test_check_upload_size_exceeds_limit(self):
        ok, msg = check_upload_size(501 * 1024)
        assert ok is False
        assert msg is not None
        assert "500 KB" in msg

    def test_get_gemini_api_key_priority(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        secrets = {"GEMINI_API_KEY": "secret-key"}
        assert get_gemini_api_key(secrets) == "secret-key"

    def test_get_gemini_api_key_env_fallback(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        assert get_gemini_api_key({}) == "env-key"
        assert get_gemini_api_key(None) == "env-key"

    def test_get_gemini_api_key_google_env_fallback(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "google-env-key")
        assert get_gemini_api_key({}) == "google-env-key"


class TestStreamlitDeprecations:
    def test_app_source_has_no_deprecated_components_or_container_width(self):
        """app.py must not contain use_container_width or components.html."""
        app_source = Path("app.py").read_text(encoding="utf-8")
        assert "use_container_width" not in app_source
        assert "components.html" not in app_source
        assert "streamlit.components.v1" not in app_source
