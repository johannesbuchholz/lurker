import hashlib
import importlib.util
import json
import os
import pkgutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from src import log
from src.action_handler import ActionHandler, LurkerContext

LOGGER = log.new_logger(__name__)

PLUGIN_MODULE_PREFIX = "_lurker_plugin_"
_REQUIREMENTS_STATE_DIR = ".plugin_state"


class PluginError(Exception):
    """Raised when a plugin cannot be provisioned, imported, or validated."""


def _discover_plugin_dirs(root: str) -> list[Path]:
    """Searches for valid __init__.py containing python packages whose names do not start with '_' or '.'."""
    root_path = Path(root)
    if not root_path.is_dir():
        return []
    return [
        root_path / info.name
        for info in sorted(pkgutil.iter_modules([str(root_path)]), key=lambda item: item.name)
        if info.ispkg
        and (root_path / info.name / "__init__.py").is_file()
        and not info.name.startswith(("_", "."))
        and info.name.isidentifier()
    ]


def _merge_plugin_dirs(*roots: str) -> list[Path]:
    merged: dict[str, Path] = {}
    for root in roots:
        for plugin_dir in _discover_plugin_dirs(root):
            merged[plugin_dir.name] = plugin_dir
    return list(merged.values())


def _read_config_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        LOGGER.warning(f"Ignoring unreadable plugin config {path}: {type(error)} {error}")
        return {}
    if not isinstance(loaded, dict):
        LOGGER.warning(f"Ignoring plugin config {path}: expected a JSON object")
        return {}
    return loaded


def load_plugin_config(name: str, base_root: str, overlay_root: str | None = None) -> dict[str, Any]:
    config = _read_config_object(Path(base_root) / "config" / f"{name}.json")
    if overlay_root is not None:
        config = config | _read_config_object(Path(overlay_root) / "config" / f"{name}.json")
    return config


def _warn_unknown_config_files(roots: list[str], plugin_names: list[str]) -> None:
    """
    Discovers config per plugin under each root (<root>/config/*.json) and matches these against known plugins.
    Files like <unknown-plugin-name>.json emit a warning if there is no plugin named "<unknown-plugin-name>".
    """
    known = set(plugin_names)
    for root in roots:
        config_dir = Path(root) / "config"
        if not config_dir.is_dir():
            continue
        for path in sorted(config_dir.glob("*.json")):
            if path.stem not in known:
                LOGGER.warning(f"Plugin config {path} has no matching plugin")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_requirements(plugin_dir: Path, lurker_home: str) -> None:
    """
    Installs dependencies of the plugin if there is a requirements.txt file.
    Stores file hashes to skip already installed requirements.
    """
    requirements = plugin_dir / "requirements.txt"
    if not requirements.is_file():
        return
    name = plugin_dir.name
    if sys.prefix == sys.base_prefix:
        raise PluginError(f"{name}: requirements.txt requires a virtualenv")
    if not sys.executable:
        raise PluginError(f"{name}: sys.executable is empty")
    if importlib.util.find_spec("pip") is None:
        raise PluginError(f"{name}: pip is not available in the running interpreter")

    expected_digest = _sha256_file(requirements)
    marker = Path(lurker_home) / _REQUIREMENTS_STATE_DIR / f"{name}.requirements.sha256"
    if marker.is_file() and marker.read_text().strip() == expected_digest:
        LOGGER.debug(f"Plugin requirements for {name} are already installed")
        return

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--require-virtualenv",
        "--disable-pip-version-check",
        "--no-input",
        "-r",
        str(requirements),
    ]
    LOGGER.info(f"Installing requirements for plugin {name}")
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise PluginError(
            f"{name}: pip install failed with exit code {completed.returncode}: "
            f"{completed.stderr[-500:]}"
        )

    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(expected_digest)
    except OSError as error:
        LOGGER.warning(f"Could not write requirements marker {marker}: {error}")
    importlib.invalidate_caches()


def _import_plugin(plugin_dir: Path) -> Any:
    module_name = f"{PLUGIN_MODULE_PREFIX}{plugin_dir.name}"
    init_file = plugin_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(module_name, init_file, submodule_search_locations=[str(plugin_dir)])
    if spec is None or spec.loader is None:
        raise PluginError(f"{plugin_dir.name}: could not create an import spec")
    module = importlib.util.module_from_spec(spec)
    _drop_plugin_module(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        _drop_plugin_module(module_name)
        raise
    return module


def _drop_plugin_module(module_name: str) -> None:
    for loaded_name in list(sys.modules):
        if loaded_name == module_name or loaded_name.startswith(f"{module_name}."):
            sys.modules.pop(loaded_name, None)


def load_handlers(
        context: LurkerContext,
        overlay_plugin_root_dir: str | None = None,
        *,
        raise_on_error: bool = False,
) -> list[ActionHandler]:
    base_root = context.plugin_root_dir
    roots = [base_root]
    if overlay_plugin_root_dir is not None and os.path.abspath(overlay_plugin_root_dir) != os.path.abspath(base_root):
        roots.append(overlay_plugin_root_dir)

    plugin_dirs = _merge_plugin_dirs(*roots)
    if not plugin_dirs:
        LOGGER.warning(f"No plugins found in {roots}; lurker will not react to instructions")
        return []

    _warn_unknown_config_files(roots, [plugin_dir.name for plugin_dir in plugin_dirs])

    handlers_by_key: dict[str, ActionHandler] = {}
    failures: list[Exception] = []
    for plugin_dir in plugin_dirs:
        name = plugin_dir.name
        module_name = f"{PLUGIN_MODULE_PREFIX}{name}"
        LOGGER.info(f"Loading plugin from {plugin_dir}")
        try:
            _ensure_requirements(plugin_dir, context.lurker_home)
            module = _import_plugin(plugin_dir)
            handler_class = getattr(module, "Handler", None)
            if not (isinstance(handler_class, type) and issubclass(handler_class, ActionHandler)):
                raise PluginError(f"{name}: __init__.py must expose Handler(ActionHandler)")

            config = load_plugin_config(name, base_root, overlay_plugin_root_dir)
            handler = handler_class(context, config)
            key = getattr(handler, "key", None)
            if not isinstance(key, str) or not key:
                raise PluginError(f"{name}: handler.key must be a non-empty string")
            handler.ensure_resources()
        except Exception as error:
            LOGGER.warning(f"Could not load plugin {name}: {type(error)} {error}", exc_info=error)
            _drop_plugin_module(module_name)
            failures.append(error)
            continue

        LOGGER.info(f"Finished loading plugin {plugin_dir}:{key}")
        if key in handlers_by_key:
            LOGGER.info(f"Plugin {name} overrides the handler for key '{key}'")
        handlers_by_key[key] = handler

    handlers = list(handlers_by_key.values())
    if not handlers:
        LOGGER.warning("No handlers loaded; lurker will not react to instructions")
    else:
        LOGGER.info(f"Loaded handlers ({len(handlers)}): {[handler.key for handler in handlers]}")
    if failures and raise_on_error:
        raise PluginError(f"{len(failures)} plugin(s) failed to load") from failures[0]
    return handlers
