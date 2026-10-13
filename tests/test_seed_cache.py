from pathlib import Path

import pytest

from cache import DiskStore, ExtractionCache, prompt_version
from seed_cache import seed

EXPECTED = [
    "0001140361-25-017410",
    "0001193125-17-024075",
    "0001193125-25-215807",
    "0001193125-26-338750",
]


def test_version_file_matches_current_prompt():
    assert Path("data/fixtures/PROMPT_VERSION").read_text(encoding="utf-8").strip() == prompt_version()


def test_seed_writes_all_four(tmp_path):
    store = DiskStore(tmp_path)
    assert seed(store) == EXPECTED
    cache = ExtractionCache(store)
    for acc in EXPECTED:
        assert cache.get(acc) is not None


def test_seed_refuses_on_version_mismatch(tmp_path):
    version_file = tmp_path / "PROMPT_VERSION"
    version_file.write_text("000000000000\n", encoding="utf-8")
    store = DiskStore(tmp_path / "store")
    with pytest.raises(RuntimeError, match="prompt"):
        seed(store, version_file=version_file)
    assert not (tmp_path / "store").exists()
