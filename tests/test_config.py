import json

from src import config as config_module
from src.config import load_lurker_config


def _write(path, payload: dict) -> None:
    path.write_text(json.dumps(payload))


def test_overlay_overrides_base(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(config_module.LURKER_LANGUAGE, raising=False)
    _write(tmp_path / "base.json", {"LURKER_LANGUAGE": "en", "LURKER_KEYWORD": ["hey john"]})
    _write(tmp_path / "overlay.json", {"LURKER_LANGUAGE": "de"})

    config = load_lurker_config(str(tmp_path / "base.json"), str(tmp_path / "overlay.json"))

    assert config.LURKER_LANGUAGE == "de"
    assert config.LURKER_KEYWORD == ["hey john"]


def test_env_overrides_base_and_overlay(tmp_path, monkeypatch) -> None:
    _write(tmp_path / "base.json", {"LURKER_LANGUAGE": "en"})
    _write(tmp_path / "overlay.json", {"LURKER_LANGUAGE": "de"})
    monkeypatch.setenv(config_module.LURKER_LANGUAGE, "fr")

    config = load_lurker_config(str(tmp_path / "base.json"), str(tmp_path / "overlay.json"))

    assert config.LURKER_LANGUAGE == "fr"


def test_handler_and_plugin_root_fields_are_gone(tmp_path) -> None:
    _write(tmp_path / "config.json", {})

    config = load_lurker_config(str(tmp_path / "config.json"))

    assert not hasattr(config, "LURKER_HANDLER_MODULE")
    assert not hasattr(config, "LURKER_HANDLER_CONFIG")
    assert not hasattr(config, "LURKER_ACTION_REFRESH_INTERVAL")
    assert not hasattr(config, "LURKER_PLUGIN_ROOT_DIR")
