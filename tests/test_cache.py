import io
from pathlib import Path

import pytest

import cache
from cache import DiskStore, R2Store, make_store, prompt_version


class FakeS3:
    """Stands in for a boto3 S3 client. Raises like botocore does on a missing key."""

    def __init__(self, fail: bool = False):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.fail = fail
        self.put_calls: list[dict] = []

    def get_object(self, Bucket, Key):
        if self.fail:
            raise ConnectionError("network down")
        if (Bucket, Key) not in self.objects:
            raise KeyError(Key)
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def put_object(self, Bucket, Key, Body, ContentType):
        if self.fail:
            raise ConnectionError("network down")
        self.put_calls.append({"Bucket": Bucket, "Key": Key, "ContentType": ContentType})
        self.objects[(Bucket, Key)] = Body

    def head_object(self, Bucket, Key):
        if self.fail:
            raise ConnectionError("network down")
        if (Bucket, Key) not in self.objects:
            raise KeyError(Key)
        return {}


class TestPromptVersion:
    def test_is_12_hex_and_stable(self):
        v = prompt_version()
        assert len(v) == 12
        assert all(c in "0123456789abcdef" for c in v)
        assert prompt_version() == v

    def test_changes_with_prompt(self):
        assert prompt_version(prompt="something else") != prompt_version()

    def test_changes_with_model(self):
        assert prompt_version(model_id="another-model") != prompt_version()


class TestDiskStore:
    def test_round_trip(self, tmp_path: Path):
        store = DiskStore(tmp_path)
        assert store.get_text("a/b.json") is None
        assert store.exists("a/b.json") is False
        store.put_text("a/b.json", "€ text")
        assert store.get_text("a/b.json") == "€ text"
        assert store.exists("a/b.json") is True

    def test_rejects_key_outside_root(self, tmp_path: Path):
        store = DiskStore(tmp_path)
        with pytest.raises(ValueError):
            store.put_text("../escape.txt", "x")


class TestR2Store:
    def test_round_trip(self):
        client = FakeS3()
        store = R2Store(client, "bucket")
        assert store.get_text("k") is None
        assert store.exists("k") is False
        store.put_text("k", "€ text")
        assert store.get_text("k") == "€ text"
        assert store.exists("k") is True
        assert client.put_calls[0] == {"Bucket": "bucket", "Key": "k", "ContentType": "text/plain; charset=utf-8"}

    def test_errors_become_misses(self):
        store = R2Store(FakeS3(fail=True), "bucket")
        assert store.get_text("k") is None
        assert store.exists("k") is False
        store.put_text("k", "x")  # must not raise


class TestMakeStore:
    def test_disk_when_secrets_missing(self, tmp_path: Path):
        assert isinstance(make_store(None, disk_root=tmp_path), DiskStore)
        assert isinstance(make_store({"R2_BUCKET": "b"}, disk_root=tmp_path), DiskStore)

    def test_disk_when_a_secret_is_blank(self, tmp_path: Path):
        secrets = {name: "x" for name in cache.R2_SECRET_NAMES}
        secrets["R2_SECRET_ACCESS_KEY"] = "  "
        assert isinstance(make_store(secrets, disk_root=tmp_path), DiskStore)

    def test_r2_when_all_secrets_present(self, monkeypatch, tmp_path: Path):
        captured = {}

        def fake_client(service, **kwargs):
            captured["service"] = service
            captured.update(kwargs)
            return FakeS3()

        monkeypatch.setattr(cache.boto3, "client", fake_client)
        secrets = {
            "R2_ACCOUNT_ID": "acct123",
            "R2_ACCESS_KEY_ID": "id",
            "R2_SECRET_ACCESS_KEY": "secret",
            "R2_BUCKET": "bucket",
        }
        store = make_store(secrets, disk_root=tmp_path)
        assert isinstance(store, R2Store)
        assert captured["service"] == "s3"
        assert captured["endpoint_url"] == "https://acct123.r2.cloudflarestorage.com"
        assert captured["region_name"] == "auto"
