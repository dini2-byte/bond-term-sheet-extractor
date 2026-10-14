"""Every test gets its own empty disk store and fresh Streamlit caches, and never sees R2 settings."""
from pathlib import Path

import pytest
import streamlit as st

from cache import CACHE_DIR_ENV, R2_SECRET_NAMES


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "store"
    monkeypatch.setenv(CACHE_DIR_ENV, str(root))
    for name in R2_SECRET_NAMES:
        monkeypatch.delenv(name, raising=False)
    st.cache_data.clear()
    st.cache_resource.clear()
    return root
