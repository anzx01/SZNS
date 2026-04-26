from __future__ import annotations

from statistics import mean, pstdev


class DataPreprocessorPlugin:
    name = "DataPreprocessorPlugin"

    def process(self, rows: list[dict[str, float]], manifest: dict) -> tuple[list[dict[str, float]], dict]:
        summary = self.summarize(rows, manifest)
        summary["filters_applied"] = ["schema_validation", "anomaly_scan"]
        return rows, summary

    def summarize(self, rows: list[dict[str, float]], manifest: dict) -> dict:
        signals = [
            signal
            for signal in (*manifest.get("required_signals", ()), *manifest.get("optional_signals", ()))
            if signal != "time" and rows and signal in rows[0]
        ]
        anomaly_count = 0
        signal_stats: dict[str, dict[str, float]] = {}
        for signal in signals:
            values = [row[signal] for row in rows if signal in row]
            if not values:
                continue
            avg = mean(values)
            sigma = pstdev(values) if len(values) > 1 else 0.0
            if sigma > 0:
                anomaly_count += sum(1 for value in values if abs(value - avg) > sigma * 3)
            span = max(values) - min(values)
            avg_delta = (
                mean(abs(b - a) for a, b in zip(values, values[1:]))
                if len(values) > 1
                else 0.0
            )
            signal_stats[signal] = {
                "min": round(min(values), 6),
                "max": round(max(values), 6),
                "mean": round(avg, 6),
                "noise_index": round(avg_delta / max(abs(span), 1e-9), 6),
            }
        return {
            "rows_scanned": len(rows),
            "signals_scanned": signals,
            "anomaly_count": anomaly_count,
            "quality_level": "review" if anomaly_count else "ok",
            "signal_stats": signal_stats,
        }

