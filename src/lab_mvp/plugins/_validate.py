from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..external_plugins import (
    SUPPORTED_EXTERNAL_TYPES,
    _REQUIRED_METHODS,
    _load_package,
    _required_text,
)


@dataclass
class ValidationResult:
    package_path: str
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    def summary(self) -> str:
        lines: list[str] = [f"{'[PASS]' if self.ok else '[FAIL]'}  {self.package_path}"]
        for msg in self.errors:
            lines.append(f"  [ERROR]   {msg}")
        for msg in self.warnings:
            lines.append(f"  [WARN]    {msg}")
        if self.ok and self.info:
            lines.append(f"  type={self.info.get('type')}  version={self.info.get('version')}  "
                         f"entrypoint={self.info.get('entrypoint')}")
        return "\n".join(lines)


def validate_package(package_path: str | Path) -> ValidationResult:
    path = Path(package_path)
    errors: list[str] = []
    warnings: list[str] = []
    info: dict = {}

    if not path.exists():
        return ValidationResult(str(path), ok=False, errors=[f"路径不存在: {path}"])
    if not path.is_dir():
        return ValidationResult(str(path), ok=False, errors=[f"路径不是目录: {path}"])

    manifest_path = path / "plugin.json"
    if not manifest_path.exists():
        return ValidationResult(str(path), ok=False, errors=["缺少 plugin.json"])

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ValidationResult(str(path), ok=False, errors=[f"plugin.json 解析失败: {exc}"])

    for required_field in ("id", "name", "type", "entrypoint"):
        try:
            _required_text(manifest, required_field)
        except ValueError:
            errors.append(f"plugin.json 缺少必填字段: {required_field}")

    plugin_type = manifest.get("type", "")
    entrypoint = manifest.get("entrypoint", "")
    info = {
        "type": plugin_type,
        "version": manifest.get("version", "?"),
        "entrypoint": entrypoint,
    }

    if plugin_type and plugin_type not in SUPPORTED_EXTERNAL_TYPES:
        errors.append(f"不支持的插件类型: {plugin_type}。支持: {', '.join(sorted(SUPPORTED_EXTERNAL_TYPES))}")

    if plugin_type == "data_source" and not manifest.get("file_extensions"):
        warnings.append("data_source 类型建议在 plugin.json 中声明 file_extensions 字段")

    if plugin_type in ("feature", "model", "constraint") and not manifest.get("experiment_type"):
        warnings.append(f"{plugin_type} 类型建议声明 experiment_type 字段")

    if entrypoint and ":" in entrypoint:
        module_name, class_name = [p.strip() for p in entrypoint.split(":", 1)]
        module_path = path / f"{module_name}.py"
        if not module_path.exists():
            errors.append(f"entrypoint 模块文件不存在: {module_path.name}")
    elif entrypoint:
        errors.append("entrypoint 格式错误，应为 模块名:类名")

    if errors:
        return ValidationResult(str(path), ok=False, errors=errors, warnings=warnings, info=info)

    package = _load_package(path, manifest_path)
    if package.instance is None:
        errors.append(package.spec.notes or "插件加载失败（原因未知）")
        return ValidationResult(str(path), ok=False, errors=errors, warnings=warnings, info=info)

    required_methods = _REQUIRED_METHODS.get(plugin_type, ())
    for method in required_methods:
        if not callable(getattr(package.instance, method, None)):
            errors.append(f"插件实例缺少必须方法: {method}()")

    return ValidationResult(
        str(path),
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        info=info,
    )
