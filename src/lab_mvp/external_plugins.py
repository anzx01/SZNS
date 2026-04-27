from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from .plugin_runtime import PluginSpec


SUPPORTED_EXTERNAL_TYPES = {"optimizer"}


@dataclass(frozen=True)
class ExternalPluginPackage:
    spec: PluginSpec
    instance: object | None = None


def discover_external_plugins(plugin_root: Path) -> list[ExternalPluginPackage]:
    if not plugin_root.exists():
        return []
    packages: list[ExternalPluginPackage] = []
    for directory in sorted(item for item in plugin_root.iterdir() if item.is_dir()):
        manifest_path = directory / "plugin.json"
        if not manifest_path.exists():
            continue
        packages.append(_load_package(directory, manifest_path))
    return packages


def _load_package(directory: Path, manifest_path: Path) -> ExternalPluginPackage:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        spec = _spec_from_manifest(directory, manifest)
        if not spec.available:
            return ExternalPluginPackage(spec)
        module_name, class_name = _entrypoint(manifest)
        module = _load_module(directory, module_name, spec.id)
        plugin_class = getattr(module, class_name)
        instance = plugin_class()
        _validate_instance(spec, instance)
        return ExternalPluginPackage(spec, instance)
    except Exception as exc:
        return ExternalPluginPackage(_error_spec(directory.name, str(exc)))


def _spec_from_manifest(directory: Path, manifest: dict[str, Any]) -> PluginSpec:
    plugin_type = _required_text(manifest, "type")
    name = _required_text(manifest, "name")
    plugin_id = str(manifest.get("id") or f"{plugin_type}:{name}")
    supported = plugin_type in SUPPORTED_EXTERNAL_TYPES
    notes = str(manifest.get("notes") or "")
    if not supported:
        notes = f"Unsupported external plugin type: {plugin_type}."
    return PluginSpec(
        id=plugin_id,
        name=name,
        type=plugin_type,
        experiment_type=manifest.get("experiment_type"),
        key=str(manifest.get("key") or name),
        source="external",
        version=str(manifest.get("version") or "0.1.0"),
        description=str(manifest.get("description") or ""),
        default_loaded=bool(manifest.get("default_loaded", True)) and supported,
        available=supported,
        notes=notes,
    )


def _entrypoint(manifest: dict[str, Any]) -> tuple[str, str]:
    value = _required_text(manifest, "entrypoint")
    if ":" not in value:
        raise ValueError("entrypoint must use module:ClassName format.")
    module_name, class_name = [part.strip() for part in value.split(":", 1)]
    if not module_name or not class_name:
        raise ValueError("entrypoint must include both module and class name.")
    return module_name.removesuffix(".py"), class_name


def _load_module(directory: Path, module_name: str, plugin_id: str) -> ModuleType:
    module_path = directory / f"{module_name}.py"
    if not module_path.exists():
        raise ValueError(f"entrypoint module not found: {module_path.name}")
    safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", plugin_id)
    import_name = f"lab_mvp_external_{safe_name}"
    spec = importlib.util.spec_from_file_location(import_name, module_path)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load module: {module_path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_instance(spec: PluginSpec, instance: object) -> None:
    if spec.type == "optimizer" and not callable(getattr(instance, "recommend", None)):
        raise ValueError("optimizer plugins must implement recommend(runs, config).")


def _required_text(manifest: dict[str, Any], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"plugin.json missing required text field: {key}")
    return value.strip()


def _error_spec(package_name: str, message: str) -> PluginSpec:
    return PluginSpec(
        id=f"external:error:{package_name}",
        name=package_name,
        type="external",
        source="external",
        default_loaded=False,
        available=False,
        notes=message,
    )
