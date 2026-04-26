from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any


REQUIRED_SIGNALS = ("time", "vgs", "vds", "ids")
OPTIONAL_SIGNALS = ("temperature",)


class DataValidationError(ValueError):
    pass


class CSVDataSourcePlugin:
    source_type = "csv"

    def load_text(self, content: str) -> list[dict[str, float]]:
        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
            raise DataValidationError("CSV 文件缺少表头。")
        rows = [self._coerce_row(row) for row in reader]
        self.validate(rows)
        return rows

    def validate(self, rows: list[dict[str, float]]) -> None:
        if not rows:
            raise DataValidationError("数据为空。")
        missing = [name for name in REQUIRED_SIGNALS if name not in rows[0]]
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

    def load_text(self, content: str) -> list[dict[str, float]]:
        payload = json.loads(content)
        if isinstance(payload, dict):
            payload = payload.get("rows", [])
        if not isinstance(payload, list):
            raise DataValidationError("JSON 数据必须是数组，或包含 rows 数组。")
        rows = [self._coerce_row(row) for row in payload]
        CSVDataSourcePlugin().validate(rows)
        return rows

    def _coerce_row(self, row: dict[str, Any]) -> dict[str, float]:
        return {key: float(value) for key, value in row.items() if value is not None}


def plugin_for_filename(filename: str):
    suffix = filename.lower().rsplit(".", 1)[-1]
    if suffix == "json":
        return JSONDataSourcePlugin()
    return CSVDataSourcePlugin()

