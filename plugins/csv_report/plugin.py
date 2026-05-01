from __future__ import annotations

import csv
import io


class CsvReportPlugin:
    """将实验 run 和推荐数据导出为 CSV，作为外部 report 插件样例。"""

    name = "CsvReportPlugin"

    def generate(
        self,
        project: dict,
        runs: list[dict],
        recommendations: list[dict],
        config: dict | None = None,
        manifest: dict | None = None,
        events: list[dict] | None = None,
    ) -> str:
        buf = io.StringIO()
        self._write_header(buf, project)
        self._write_runs(buf, runs)
        self._write_recommendations(buf, recommendations)
        self._write_events(buf, events or [])
        return buf.getvalue()

    def _write_header(self, buf: io.StringIO, project: dict) -> None:
        buf.write(f"# 项目,{project.get('name', '')}\n")
        buf.write(f"# 实验类型,{project.get('experiment_type', '')}\n")
        buf.write(f"# 导出时间,{project.get('updated_at', '')}\n")
        buf.write("\n")

    def _write_runs(self, buf: io.StringIO, runs: list[dict]) -> None:
        if not runs:
            return
        all_metric_keys: list[str] = []
        for run in runs:
            for key in run.get("metrics", {}):
                if key not in all_metric_keys:
                    all_metric_keys.append(key)

        writer = csv.writer(buf)
        writer.writerow(["## Runs"])
        writer.writerow(["run_id", "label", "source_type", "created_at"] + all_metric_keys)
        for run in runs:
            metrics = run.get("metrics", {})
            writer.writerow([
                run.get("id", ""),
                run.get("label", ""),
                run.get("source_type", ""),
                run.get("created_at", ""),
            ] + [metrics.get(k, "") for k in all_metric_keys])
        buf.write("\n")

    def _write_recommendations(self, buf: io.StringIO, recommendations: list[dict]) -> None:
        if not recommendations:
            return
        all_param_keys: list[str] = []
        for rec in recommendations:
            for key in rec.get("recommended_parameters", {}):
                if key not in all_param_keys:
                    all_param_keys.append(key)

        writer = csv.writer(buf)
        writer.writerow(["## 推荐记录"])
        writer.writerow(["rec_id", "optimizer", "safety_passed", "decision", "created_at"] + all_param_keys)
        for rec in recommendations:
            params = rec.get("recommended_parameters", {})
            safety = rec.get("safety_result", {})
            writer.writerow([
                rec.get("id", ""),
                rec.get("optimizer", ""),
                safety.get("passed", ""),
                rec.get("decision", "pending"),
                rec.get("created_at", ""),
            ] + [params.get(k, "") for k in all_param_keys])
        buf.write("\n")

    def _write_events(self, buf: io.StringIO, events: list[dict]) -> None:
        if not events:
            return
        writer = csv.writer(buf)
        writer.writerow(["## 事件日志"])
        writer.writerow(["created_at", "type", "message"])
        for event in events:
            writer.writerow([
                event.get("created_at", ""),
                event.get("type", ""),
                event.get("message", ""),
            ])
