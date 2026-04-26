from __future__ import annotations

import csv
import json
from io import StringIO
import re
from typing import Any


REQUIRED_SIGNALS = ("time", "vgs", "vds", "ids")
OPTIONAL_SIGNALS = ("temperature",)


class DataValidationError(ValueError):
    pass


class CSVDataSourcePlugin:
    source_type = "csv"

    def load_text(
        self,
        content: str,
        required_signals: tuple[str, ...] = REQUIRED_SIGNALS,
        field_mapping: dict[str, str] | None = None,
    ) -> list[dict[str, float]]:
        rows = self._parse_rows(content)
        rows = _apply_field_mapping(rows, field_mapping)
        self.validate(rows, required_signals)
        return rows

    def preview_text(
        self,
        content: str,
        required_signals: tuple[str, ...] = REQUIRED_SIGNALS,
        optional_signals: tuple[str, ...] = OPTIONAL_SIGNALS,
        field_mapping: dict[str, str] | None = None,
        field_aliases: dict[str, tuple[str, ...]] | None = None,
    ) -> dict:
        errors: list[str] = []
        try:
            reader = csv.DictReader(StringIO(content))
            fieldnames = [name.strip() for name in (reader.fieldnames or []) if name]
            if not fieldnames:
                return _preview_result(self.source_type, [], [], required_signals, optional_signals, ["CSV 文件缺少表头。"])
            rows = [self._coerce_row(row) for row in reader]
        except ValueError as exc:
            fieldnames = []
            rows = []
            errors.append(f"存在非数值字段：{exc}")
        return _preview_result(
            self.source_type,
            fieldnames,
            rows,
            required_signals,
            optional_signals,
            errors,
            field_mapping,
            field_aliases,
        )

    def _parse_rows(self, content: str) -> list[dict[str, float]]:
        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
            raise DataValidationError("CSV 文件缺少表头。")
        return [self._coerce_row(row) for row in reader]

    def validate(self, rows: list[dict[str, float]], required_signals: tuple[str, ...] = REQUIRED_SIGNALS) -> None:
        if not rows:
            raise DataValidationError("数据为空。")
        missing = [name for name in required_signals if name not in rows[0]]
        if missing:
            raise DataValidationError(f"缺少必要字段：{', '.join(missing)}")

    def _coerce_row(self, row: dict[str, Any]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for key, value in row.items():
            if key is None or key == "":
                continue
            if value is None or str(value).strip() == "":
                continue
            normalized[key.strip()] = float(value)
        return normalized


class JSONDataSourcePlugin:
    source_type = "json"

    def load_text(
        self,
        content: str,
        required_signals: tuple[str, ...] = REQUIRED_SIGNALS,
        field_mapping: dict[str, str] | None = None,
    ) -> list[dict[str, float]]:
        rows = self._parse_rows(content)
        rows = _apply_field_mapping(rows, field_mapping)
        CSVDataSourcePlugin().validate(rows, required_signals)
        return rows

    def preview_text(
        self,
        content: str,
        required_signals: tuple[str, ...] = REQUIRED_SIGNALS,
        optional_signals: tuple[str, ...] = OPTIONAL_SIGNALS,
        field_mapping: dict[str, str] | None = None,
        field_aliases: dict[str, tuple[str, ...]] | None = None,
    ) -> dict:
        errors: list[str] = []
        try:
            payload = self._payload(content)
            fieldnames = sorted({key for row in payload if isinstance(row, dict) for key in row})
            rows = [self._coerce_row(row) for row in payload]
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            fieldnames = []
            rows = []
            errors.append(str(exc))
        return _preview_result(
            self.source_type,
            fieldnames,
            rows,
            required_signals,
            optional_signals,
            errors,
            field_mapping,
            field_aliases,
        )

    def _parse_rows(self, content: str) -> list[dict[str, float]]:
        payload = self._payload(content)
        return [self._coerce_row(row) for row in payload]

    def _payload(self, content: str) -> list[dict[str, Any]]:
        payload = json.loads(content)
        if isinstance(payload, dict):
            payload = payload.get("rows", [])
        if not isinstance(payload, list):
            raise DataValidationError("JSON 数据必须是数组，或包含 rows 数组。")
        if any(not isinstance(row, dict) for row in payload):
            raise DataValidationError("JSON rows 中的每一项都必须是对象。")
        return payload

    def _coerce_row(self, row: dict[str, Any]) -> dict[str, float]:
        return {key: float(value) for key, value in row.items() if value is not None}


def plugin_for_filename(filename: str):
    suffix = filename.lower().rsplit(".", 1)[-1]
    if suffix == "json":
        return JSONDataSourcePlugin()
    return CSVDataSourcePlugin()


def _preview_result(
    source_type: str,
    fieldnames: list[str],
    rows: list[dict[str, float]],
    required_signals: tuple[str, ...],
    optional_signals: tuple[str, ...],
    errors: list[str] | None = None,
    field_mapping: dict[str, str] | None = None,
    field_aliases: dict[str, tuple[str, ...]] | None = None,
) -> dict:
    error_list = list(errors or [])
    expected_signals = [*required_signals, *optional_signals]
    active_mapping = _clean_mapping(
        field_mapping or _suggest_field_mapping(fieldnames, expected_signals, field_aliases or {})
    )
    mapped_rows = _apply_field_mapping(rows, active_mapping)
    mapped_fieldnames = sorted({key for row in mapped_rows for key in row})
    missing = [name for name in required_signals if name not in mapped_fieldnames]
    expected = {*required_signals, *optional_signals}
    extra = [name for name in fieldnames if name not in expected]
    if missing:
        error_list.append(f"缺少必要字段：{', '.join(missing)}")
    if not rows:
        error_list.append("数据为空。")
    return {
        "source_type": source_type,
        "valid": not error_list,
        "errors": error_list,
        "rows": len(rows),
        "fieldnames": fieldnames,
        "mapped_fieldnames": mapped_fieldnames,
        "required_signals": list(required_signals),
        "optional_signals": list(optional_signals),
        "field_mapping": active_mapping,
        "missing": missing,
        "extra": extra,
        "preview_rows": mapped_rows[:5],
    }


def _apply_field_mapping(rows: list[dict[str, float]], field_mapping: dict[str, str] | None) -> list[dict[str, float]]:
    mapping = _clean_mapping(field_mapping)
    if not mapping:
        return rows
    mapped_rows: list[dict[str, float]] = []
    mapped_sources = {source for source in mapping.values() if source}
    for row in rows:
        mapped: dict[str, float] = {}
        for canonical, source in mapping.items():
            if source in row:
                mapped[canonical] = row[source]
        for key, value in row.items():
            if key not in mapped_sources and key not in mapped:
                mapped[key] = value
        mapped_rows.append(mapped)
    return mapped_rows


def _clean_mapping(field_mapping: dict[str, str] | None) -> dict[str, str]:
    if not field_mapping:
        return {}
    return {
        str(canonical): str(source)
        for canonical, source in field_mapping.items()
        if canonical and source
    }


def _suggest_field_mapping(
    fieldnames: list[str],
    expected_signals: list[str],
    field_aliases: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    normalized_fields = {_normalize_field(name): name for name in fieldnames}
    mapping: dict[str, str] = {}
    for signal in expected_signals:
        candidates = [signal, *field_aliases.get(signal, ())]
        for candidate in candidates:
            matched = normalized_fields.get(_normalize_field(candidate))
            if matched:
                mapping[signal] = matched
                break
    return mapping


def _normalize_field(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())
