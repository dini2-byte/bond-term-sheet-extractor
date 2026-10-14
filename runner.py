"""
Loads a saved extraction or runs a new one, charging the run budget only for real Gemini calls.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache import MODEL_ID, ExtractionCache
import extract
from lookup import RunBudget


def extract_terms(*args: Any, **kwargs: Any) -> Any:
    return extract.extract_terms(*args, **kwargs)

logger = logging.getLogger(__name__)

NO_KEY_MESSAGE = "Live extraction is not set up on this deployment."
FAILED_MESSAGE = "The extraction did not finish. Your run was not counted."


@dataclass(frozen=True)
class RunOutcome:
    jsonl_path: Path | None
    from_cache: bool
    charged: bool
    error: str | None


def _run_live(
    filing_text: str,
    stem: str,
    budget: RunBudget,
    session_runs: int,
    api_key: str | None,
    work_dir: Path,
    extract_fn: Callable[..., Any],
) -> RunOutcome:
    """One real Gemini run. Charges the budget only when the extractor wrote its JSONL."""
    can_run, reason = budget.can_run(session_runs)
    if not can_run:
        return RunOutcome(None, from_cache=False, charged=False, error=reason)
    if not api_key:
        return RunOutcome(None, from_cache=False, charged=False, error=NO_KEY_MESSAGE)

    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    work = Path(work_dir)
    filing_path = work / f"{stem}.txt"
    filing_path.write_text(filing_text, encoding="utf-8")
    jsonl_path = work / f"{stem}_extractions.jsonl"
    try:
        extract_fn(filing_path, model_id=MODEL_ID, log_attempt=False, output_dir=work)
    except Exception as e:
        logger.warning("Extraction failed for %s (%s)", stem, type(e).__name__)
        return RunOutcome(None, from_cache=False, charged=False, error=FAILED_MESSAGE)
    if not jsonl_path.is_file():
        logger.warning("Extraction for %s wrote no output", stem)
        return RunOutcome(None, from_cache=False, charged=False, error=FAILED_MESSAGE)

    budget.record_run()
    return RunOutcome(jsonl_path, from_cache=False, charged=True, error=None)


def get_or_extract(
    accession: str,
    filing_text: str,
    stem: str,
    cache: ExtractionCache,
    budget: RunBudget,
    session_runs: int,
    api_key: str | None,
    work_dir: Path,
    extract_fn: Callable[..., Any] = extract_terms,
) -> RunOutcome:
    """A saved extraction when there is one (free), else a live run that is then saved."""
    saved = cache.get(accession)
    if saved is not None:
        jsonl_path = Path(work_dir) / f"{stem}_extractions.jsonl"
        jsonl_path.write_text(saved, encoding="utf-8")
        return RunOutcome(jsonl_path, from_cache=True, charged=False, error=None)

    outcome = _run_live(filing_text, stem, budget, session_runs, api_key, work_dir, extract_fn)
    if outcome.charged and outcome.jsonl_path is not None:
        try:
            cache.put(accession, outcome.jsonl_path.read_text(encoding="utf-8"))
        except ValueError:
            logger.warning("Extractor output for %s was not saved: not valid JSONL", accession)
    return outcome


def run_upload(
    filing_text: str,
    stem: str,
    budget: RunBudget,
    session_runs: int,
    api_key: str | None,
    work_dir: Path,
    extract_fn: Callable[..., Any] = extract_terms,
) -> RunOutcome:
    """A live run on an uploaded term sheet. Never read from or written to the cache."""
    return _run_live(filing_text, stem, budget, session_runs, api_key, work_dir, extract_fn)
