"""
Saves the 4 benchmark fixtures into the extraction cache so those filings load without a Gemini call.
Refuses to run if the prompt changed since the fixtures were made.

Usage: python seed_cache.py   (uses R2 when the R2 secrets are in the environment, else .cache/)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from cache import ExtractionCache, ObjectStore, make_store, prompt_version
from fetch import DEALS_TO_FETCH


def seed(
    store: ObjectStore,
    fixtures_dir: Path = Path("data/fixtures"),
    version_file: Path = Path("data/fixtures/PROMPT_VERSION"),
) -> list[str]:
    expected = Path(version_file).read_text(encoding="utf-8").strip()
    current = prompt_version()
    if expected != current:
        raise RuntimeError(
            f"The prompt changed since the fixtures were made ({expected} vs {current}). "
            "Regenerate the fixtures and update PROMPT_VERSION first."
        )
    cache = ExtractionCache(store, version=current)
    written: list[str] = []
    for deal in DEALS_TO_FETCH:
        matches = sorted(Path(fixtures_dir).glob(f"{deal['label']}_*_extractions.jsonl"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one fixture for {deal['label']}, found {len(matches)}.")
        cache.put(deal["accession"], matches[0].read_text(encoding="utf-8"))
        written.append(deal["accession"])
    return written


if __name__ == "__main__":
    load_dotenv()
    store = make_store(os.environ)
    try:
        accessions = seed(store)
    except RuntimeError as e:
        print(f"Not seeded: {e}")
        sys.exit(1)
    print(f"Seeded {len(accessions)} filings into {type(store).__name__} under prompt version {prompt_version()}.")
