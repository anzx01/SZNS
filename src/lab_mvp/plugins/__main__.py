"""CLI entry point: python -m lab_mvp.plugins <command> [args...]

Commands:
  validate <package_path> [<package_path>...]
      校验一个或多个外部插件包是否符合接口规范。

  list <plugins_dir>
      扫描目录下所有插件包并汇总校验结果。
"""
from __future__ import annotations

import sys
from pathlib import Path

from ._validate import validate_package


def _cmd_validate(paths: list[str]) -> int:
    if not paths:
        print("用法: python -m lab_mvp.plugins validate <package_path> [...]", file=sys.stderr)
        return 2
    failed = 0
    for p in paths:
        result = validate_package(p)
        print(result.summary())
        if not result.ok:
            failed += 1
    if len(paths) > 1:
        total = len(paths)
        passed = total - failed
        print(f"\n合计: {passed}/{total} 通过", "✓" if failed == 0 else "✗")
    return 1 if failed else 0


def _cmd_list(args: list[str]) -> int:
    if not args:
        print("用法: python -m lab_mvp.plugins list <plugins_dir>", file=sys.stderr)
        return 2
    plugins_dir = Path(args[0])
    if not plugins_dir.exists():
        print(f"目录不存在: {plugins_dir}", file=sys.stderr)
        return 1
    packages = sorted(item for item in plugins_dir.iterdir() if item.is_dir() and (item / "plugin.json").exists())
    if not packages:
        print(f"在 {plugins_dir} 中未找到插件包")
        return 0
    return _cmd_validate([str(p) for p in packages])


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    command, *rest = args
    if command == "validate":
        return _cmd_validate(rest)
    if command == "list":
        return _cmd_list(rest)
    print(f"未知命令: {command}\n{__doc__}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
