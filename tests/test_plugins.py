import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src import plugins
from src.action_handler import ActionHandler, LurkerContext

HANDLER_TEMPLATE = '''\
from src.action_handler import ActionHandler


class PluginHandler(ActionHandler):
    key = {key!r}

    def __init__(self, context, config):
        super().__init__(context)
        self.received_config = config

    def accepts(self, instruction):
        return {needle!r} in instruction

    def handle(self, instruction):
        return {exit_code}
'''

DEFAULT_INIT = "from .handler import PluginHandler as Handler\n\n__all__ = [\"Handler\"]\n"


def _write_plugin(
    root: Path,
    name: str,
    *,
    key: str = "plugin",
    needle: str = "time",
    exit_code: int = 0,
    handler_source: str | None = None,
    init_source: str = DEFAULT_INIT,
    requirements: str | None = None,
) -> Path:
    plugin_dir = root / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "__init__.py").write_text(init_source)
    source = handler_source or HANDLER_TEMPLATE.format(key=key, needle=needle, exit_code=exit_code)
    (plugin_dir / "handler.py").write_text(source)
    if requirements is not None:
        (plugin_dir / "requirements.txt").write_text(requirements)
    importlib.invalidate_caches()
    return plugin_dir


def _write_config(root: Path, name: str, payload) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / f"{name}.json").write_text(json.dumps(payload))


def _context(root: Path, plugin_root: Path | None = None) -> LurkerContext:
    return LurkerContext(
        lurker_home=str(root),
        plugin_root_dir=str(plugin_root or root / "plugins"),
        log_level="INFO",
        language="en",
    )


def _plugin_root(tmp_path: Path) -> Path:
    root = tmp_path / "plugins"
    root.mkdir()
    return root


def test_discover_only_directory_packages(tmp_path):
    root = _plugin_root(tmp_path)
    for name in ("zeta", "alpha", "_disabled", ".hidden"):
        _write_plugin(root, name)
    (root / "config").mkdir()
    (root / "config" / "lights.json").write_text("{}")
    (root / "single_file.py").write_text("x = 1\n")
    importlib.invalidate_caches()

    assert [path.name for path in plugins._discover_plugin_dirs(str(root))] == ["alpha", "zeta"]


def test_missing_root_yields_no_plugins(tmp_path):
    assert plugins._discover_plugin_dirs(str(tmp_path / "missing")) == []
    assert plugins.load_handlers(_context(tmp_path)) == []


def test_relative_imports_and_context(tmp_path):
    root = _plugin_root(tmp_path)
    _write_plugin(root, "clock", key="clock", needle="time")
    context = _context(tmp_path)

    handlers = plugins.load_handlers(context)

    assert [handler.key for handler in handlers] == ["clock"]
    assert isinstance(handlers[0], ActionHandler)
    assert handlers[0].context is context
    assert handlers[0].accepts("what time is it")


def test_overlay_replaces_base_plugin_and_adds_overlay_only(tmp_path):
    base = _plugin_root(tmp_path)
    overlay = tmp_path / "overlay"
    (overlay / "plugins").mkdir(parents=True)

    _write_plugin(base, "lights", key="base-key")
    _write_plugin(overlay / "plugins", "lights", key="overlay-key")
    _write_plugin(overlay / "plugins", "extra", key="extra-key")
    importlib.invalidate_caches()

    handlers = plugins.load_handlers(_context(tmp_path), str(overlay / "plugins"))

    assert sorted(handler.key for handler in handlers) == ["extra-key", "overlay-key"]


def test_base_plugin_loads_when_overlay_only_has_config(tmp_path):
    base = _plugin_root(tmp_path)
    overlay_plugins = tmp_path / "overlay" / "plugins"
    overlay_plugins.mkdir(parents=True)

    _write_plugin(base, "lights", key="lights")
    _write_config(base, "lights", {"backend": "dummy", "value": "base"})
    _write_config(overlay_plugins, "lights", {"value": "overlay"})
    importlib.invalidate_caches()

    handlers = plugins.load_handlers(_context(tmp_path), str(overlay_plugins))

    assert [handler.key for handler in handlers] == ["lights"]
    assert handlers[0].received_config == {"backend": "dummy", "value": "overlay"}


def test_plugin_config_missing_and_non_object_are_empty(tmp_path, caplog):
    root = _plugin_root(tmp_path)
    _write_plugin(root, "lights", key="lights")
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "lights.json").write_text("[]")
    importlib.invalidate_caches()

    handlers = plugins.load_handlers(_context(tmp_path))

    assert handlers[0].received_config == {}
    assert "expected a JSON object" in caplog.text


def test_unknown_config_file_warns(tmp_path, caplog):
    root = _plugin_root(tmp_path)
    _write_plugin(root, "lights", key="lights")
    _write_config(root, "ghost", {"x": 1})
    importlib.invalidate_caches()

    plugins.load_handlers(_context(tmp_path))

    assert "has no matching plugin" in caplog.text


def test_invalid_handlers_are_skipped_and_others_load(tmp_path):
    root = _plugin_root(tmp_path)
    _write_plugin(root, "good", key="good")
    _write_plugin(root, "missing-handler", init_source="")
    _write_plugin(root, "not-a-class", init_source="Handler = 42\n")
    _write_plugin(root, "not-a-handler", init_source="class Handler:\n    key = 'x'\n")
    _write_plugin(root, "empty-key", key="")
    _write_plugin(
        root,
        "constructor-raises",
        handler_source=(
            "from src.action_handler import ActionHandler\n"
            "class PluginHandler(ActionHandler):\n"
            "    key = 'broken'\n"
            "    def __init__(self, context, config):\n"
            "        raise RuntimeError('boom')\n"
            "    def accepts(self, instruction):\n"
            "        return True\n"
            "    def handle(self, instruction):\n"
            "        return 0\n"
        ),
    )
    importlib.invalidate_caches()

    handlers = plugins.load_handlers(_context(tmp_path))

    assert [handler.key for handler in handlers] == ["good"]


def test_ensure_resources_failure_skips_plugin(tmp_path):
    root = _plugin_root(tmp_path)
    _write_plugin(root, "good", key="good")
    _write_plugin(
        root,
        "resource_hungry",
        handler_source=(
            "from src.action_handler import ActionHandler\n"
            "class PluginHandler(ActionHandler):\n"
            "    key = 'hungry'\n"
            "    def ensure_resources(self):\n"
            "        raise RuntimeError('no network')\n"
            "    def accepts(self, instruction):\n"
            "        return True\n"
            "    def handle(self, instruction):\n"
            "        return 0\n"
        ),
    )
    importlib.invalidate_caches()

    handlers = plugins.load_handlers(_context(tmp_path))

    assert [handler.key for handler in handlers] == ["good"]


def test_raise_on_error_raises_after_loading_other_plugins(tmp_path):
    root = _plugin_root(tmp_path)
    _write_plugin(root, "good", key="good")
    _write_plugin(
        root,
        "resource_hungry",
        handler_source=(
            "from src.action_handler import ActionHandler\n"
            "class PluginHandler(ActionHandler):\n"
            "    key = 'hungry'\n"
            "    def __init__(self, context, config):\n"
            "        super().__init__(context)\n"
            "    def ensure_resources(self):\n"
            "        raise RuntimeError('no network')\n"
            "    def accepts(self, instruction):\n"
            "        return True\n"
            "    def handle(self, instruction):\n"
            "        return 0\n"
        ),
    )
    importlib.invalidate_caches()

    with pytest.raises(plugins.PluginError):
        plugins.load_handlers(_context(tmp_path), raise_on_error=True)


def test_ensure_resources_is_called_once_per_handler(tmp_path):
    root = _plugin_root(tmp_path)
    marker = tmp_path / "resources-called.txt"
    _write_plugin(
        root,
        "lights",
        handler_source=(
            "from src.action_handler import ActionHandler\n"
            "class PluginHandler(ActionHandler):\n"
            "    key = 'lights'\n"
            "    def __init__(self, context, config):\n"
            "        super().__init__(context)\n"
            "    def ensure_resources(self):\n"
            f"        with open({str(marker)!r}, 'a') as marker:\n"
            "            marker.write('x')\n"
            "    def accepts(self, instruction):\n"
            "        return True\n"
            "    def handle(self, instruction):\n"
            "        return 0\n"
        ),
    )
    importlib.invalidate_caches()

    plugins.load_handlers(_context(tmp_path))

    assert marker.read_text() == "x"


def test_duplicate_keys_later_plugin_wins(tmp_path):
    root = _plugin_root(tmp_path)
    _write_plugin(root, "first", key="same")
    _write_plugin(root, "second", key="same")
    importlib.invalidate_caches()

    handlers = plugins.load_handlers(_context(tmp_path))

    assert [handler.key for handler in handlers] == ["same"]


def test_failed_import_is_removed_from_sys_modules(tmp_path):
    root = _plugin_root(tmp_path)
    _write_plugin(root, "broken", init_source="raise RuntimeError('nope')\n")
    importlib.invalidate_caches()

    plugins.load_handlers(_context(tmp_path))

    assert "_lurker_plugin_broken" not in sys.modules


def _requirements_plugin(tmp_path: Path, *, requirements: str = "requests==2.0\n") -> Path:
    root = _plugin_root(tmp_path)
    _write_plugin(root, "with_requirements", key="requirements", requirements=requirements)
    importlib.invalidate_caches()
    return root


def test_requirements_skipped_outside_virtualenv(tmp_path, monkeypatch):
    root = _requirements_plugin(tmp_path)
    monkeypatch.setattr(sys, "prefix", "/usr")
    monkeypatch.setattr(sys, "base_prefix", "/usr")
    calls = []
    monkeypatch.setattr(plugins.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    handlers = plugins.load_handlers(_context(tmp_path))

    assert handlers == []
    assert calls == []


def test_requirements_skipped_without_pip(tmp_path, monkeypatch):
    _requirements_plugin(tmp_path)
    monkeypatch.setattr(plugins.importlib.util, "find_spec", lambda name: None)
    calls = []
    monkeypatch.setattr(plugins.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    handlers = plugins.load_handlers(_context(tmp_path))

    assert handlers == []
    assert calls == []


def test_requirements_install_command_and_marker(tmp_path, monkeypatch):
    root = _requirements_plugin(tmp_path)
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(plugins.subprocess, "run", fake_run)

    handlers = plugins.load_handlers(_context(tmp_path))

    assert [handler.key for handler in handlers] == ["requirements"]
    assert len(commands) == 1
    command = commands[0]
    assert command[0] == sys.executable
    assert command[1:3] == ["-m", "pip"]
    assert "--require-virtualenv" in command
    assert command[-2:] == ["-r", str(root / "with_requirements" / "requirements.txt")]

    marker = tmp_path / ".plugin_state" / "with_requirements.requirements.sha256"
    assert marker.is_file()
    expected = hashlib.sha256((root / "with_requirements" / "requirements.txt").read_bytes()).hexdigest()
    assert marker.read_text() == expected


def test_matching_marker_skips_pip(tmp_path, monkeypatch):
    root = _requirements_plugin(tmp_path)
    requirements = root / "with_requirements" / "requirements.txt"
    marker = tmp_path / ".plugin_state" / "with_requirements.requirements.sha256"
    marker.parent.mkdir(parents=True)
    marker.write_text(hashlib.sha256(requirements.read_bytes()).hexdigest())
    calls = []
    monkeypatch.setattr(plugins.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    handlers = plugins.load_handlers(_context(tmp_path))

    assert [handler.key for handler in handlers] == ["requirements"]
    assert calls == []


def test_changed_requirements_reinstall(tmp_path, monkeypatch):
    root = _requirements_plugin(tmp_path)
    marker = tmp_path / ".plugin_state" / "with_requirements.requirements.sha256"
    marker.parent.mkdir(parents=True)
    marker.write_text("stale")
    commands = []
    monkeypatch.setattr(
        plugins.subprocess,
        "run",
        lambda command, **kwargs: (
            commands.append(command) or subprocess.CompletedProcess(command, 0, "", "")
        ),
    )

    plugins.load_handlers(_context(tmp_path))

    assert len(commands) == 1


def test_pip_failure_skips_only_that_plugin(tmp_path, monkeypatch):
    root = _requirements_plugin(tmp_path)
    _write_plugin(root, "good", key="good")
    importlib.invalidate_caches()
    monkeypatch.setattr(
        plugins.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, "", "boom"),
    )

    handlers = plugins.load_handlers(_context(tmp_path))

    assert [handler.key for handler in handlers] == ["good"]


def test_empty_sys_executable_skips_plugin(tmp_path, monkeypatch):
    _requirements_plugin(tmp_path)
    monkeypatch.setattr(sys, "executable", "")
    calls = []
    monkeypatch.setattr(plugins.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    handlers = plugins.load_handlers(_context(tmp_path))

    assert handlers == []
    assert calls == []
