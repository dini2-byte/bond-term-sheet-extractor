"""
Saved extractions and small shared state, kept in an object store.
DiskStore is used locally and in tests; R2Store is used on the deployed app.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import boto3

from fields import FEW_SHOT_EXAMPLES, PROMPT_DESCRIPTION

logger = logging.getLogger(__name__)

MODEL_ID = "gemini-3.5-flash-lite"
R2_SECRET_NAMES = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
PROMPT_VERSION_LENGTH = 12


def prompt_version(
    prompt: str = PROMPT_DESCRIPTION,
    examples: list = FEW_SHOT_EXAMPLES,
    model_id: str = MODEL_ID,
) -> str:
    """Short hash of everything that shapes an extraction. Changes when the prompt, examples or model change."""
    payload = json.dumps(
        {
            "prompt": prompt,
            "examples": [dataclasses.asdict(e) for e in examples],
            "model": model_id,
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:PROMPT_VERSION_LENGTH]


class ObjectStore(Protocol):
    def get_text(self, key: str) -> str | None: ...
    def put_text(self, key: str, text: str) -> None: ...
    def exists(self, key: str) -> bool: ...


class DiskStore:
    """Keeps objects as files under root. Keys use forward slashes."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Key escapes the store root: {key!r}")
        return path

    def get_text(self, key: str) -> str | None:
        path = self._path(key)
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def put_text(self, key: str, text: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class R2Store:
    """Cloudflare R2 through the S3 API. Any error is logged and treated as a miss."""

    def __init__(self, client: Any, bucket: str):
        self.client = client
        self.bucket = bucket

    def get_text(self, key: str) -> str | None:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
            return obj["Body"].read().decode("utf-8")
        except Exception as e:
            logger.info("R2 read miss for %s (%s)", key, type(e).__name__)
            return None

    def put_text(self, key: str, text: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=text.encode("utf-8"),
                ContentType="text/plain; charset=utf-8",
            )
        except Exception as e:
            logger.warning("R2 write failed for %s (%s)", key, type(e).__name__)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def make_store(secrets: Mapping[str, Any] | None, disk_root: Path = Path(".cache")) -> ObjectStore:
    """R2Store when all four R2 secrets are set and non-blank, otherwise DiskStore."""
    values = {name: str((secrets or {}).get(name) or "").strip() for name in R2_SECRET_NAMES}
    if not all(values.values()):
        return DiskStore(disk_root)
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{values['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=values["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=values["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    return R2Store(client, values["R2_BUCKET"])


ACCESSION_PATTERN = re.compile(r"^\d{10}-\d{2}-\d{6}$")


def is_valid_extraction_jsonl(text: str | None) -> bool:
    """True when the first line is a JSON object with an extractions list and a text string."""
    if not text or not text.strip():
        return False
    try:
        doc = json.loads(text.strip().splitlines()[0])
    except (json.JSONDecodeError, IndexError):
        return False
    return isinstance(doc, dict) and isinstance(doc.get("extractions"), list) and isinstance(doc.get("text"), str)


class ExtractionCache:
    """Extractor output saved per SEC accession number, separated by prompt version."""

    def __init__(self, store: ObjectStore, version: str | None = None):
        self.store = store
        self.version = version or prompt_version()

    def key(self, accession: str) -> str:
        if not ACCESSION_PATTERN.match(accession or ""):
            raise ValueError(f"Not an SEC accession number: {accession!r}")
        return f"extractions/{self.version}/{accession}.jsonl"

    def get(self, accession: str) -> str | None:
        try:
            k = self.key(accession)
        except ValueError:
            return None
        text = self.store.get_text(k)
        if text is None:
            return None
        if not is_valid_extraction_jsonl(text):
            logger.warning("Ignoring a broken saved extraction for %s", accession)
            return None
        return text

    def put(self, accession: str, jsonl: str) -> None:
        if not is_valid_extraction_jsonl(jsonl):
            raise ValueError("Refusing to save output that is not extractor JSONL.")
        self.store.put_text(self.key(accession), jsonl)

    def has(self, accession: str) -> bool:
        try:
            return self.store.exists(self.key(accession))
        except ValueError:
            return False

