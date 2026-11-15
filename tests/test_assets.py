import io
import os

import pytest

from src import assets


def _response(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)


def test_present_file_is_returned_without_download(tmp_path, monkeypatch):
    target = tmp_path / "models" / "model.onnx"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing")

    def fail(*args, **kwargs):
        raise AssertionError("urlopen must not be called")

    monkeypatch.setattr(assets.urllib.request, "urlopen", fail)

    assert assets.ensure_asset(str(tmp_path), "models/model.onnx", "http://example/model") == str(target)


def test_missing_file_is_downloaded_atomically(tmp_path, monkeypatch):
    calls = []

    def fake_urlopen(url, timeout=None):
        calls.append(url)
        return _response(b"downloaded")

    monkeypatch.setattr(assets.urllib.request, "urlopen", fake_urlopen)

    result = assets.ensure_asset(str(tmp_path), "models/model.onnx", "http://example/model")

    assert result == str(tmp_path / "models" / "model.onnx")
    with open(result, "rb") as downloaded:
        assert downloaded.read() == b"downloaded"
    assert calls == ["http://example/model"]
    assert not list((tmp_path / "models").glob(".download-*"))


def test_checksum_is_verified(tmp_path, monkeypatch):
    monkeypatch.setattr(
        assets.urllib.request, "urlopen", lambda url, timeout=None: _response(b"payload")
    )

    with pytest.raises(ValueError):
        assets.ensure_asset(str(tmp_path), "model.onnx", "http://example/model", sha256="0" * 64)

    assert not (tmp_path / "model.onnx").exists()
    assert not list(tmp_path.glob(".download-*"))


def test_failure_leaves_no_partial_file(tmp_path, monkeypatch):
    def failing_urlopen(url, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(assets.urllib.request, "urlopen", failing_urlopen)

    with pytest.raises(OSError):
        assets.ensure_asset(str(tmp_path), "model.onnx", "http://example/model")

    assert not (tmp_path / "model.onnx").exists()
    assert not list(tmp_path.glob(".download-*"))


def test_second_call_is_a_noop(tmp_path, monkeypatch):
    calls = []

    def fake_urlopen(url, timeout=None):
        calls.append(url)
        return _response(b"downloaded")

    monkeypatch.setattr(assets.urllib.request, "urlopen", fake_urlopen)

    assets.ensure_asset(str(tmp_path), "model.onnx", "http://example/model")
    assets.ensure_asset(str(tmp_path), "model.onnx", "http://example/model")

    assert calls == ["http://example/model"]
