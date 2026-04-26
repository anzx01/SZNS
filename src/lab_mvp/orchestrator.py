from __future__ import annotations

import json
from pathlib import Path

from .constraints import SiCGaNConstraintPlugin
from .data_plugins import plugin_for_filename
from .features import SiCGaNFeaturePlugin
from .models import default_sic_gan_config, new_id, utcnow
from .optimizer import HeuristicOptimizerPlugin
from .reports import HTMLReportPlugin
from .storage import JsonStore


class ExperimentOrchestrator:
    def __init__(self, store: JsonStore, sample_dir: Path):
        self.store = store
        self.sample_dir = sample_dir
        self.feature_plugin = SiCGaNFeaturePlugin()
        self.optimizer = HeuristicOptimizerPlugin()
        self.constraints = SiCGaNConstraintPlugin()
        self.reporter = HTMLReportPlugin()

    def state(self) -> dict:
        db = self.store.all()
        projects = []
        for project in db["projects"]:
            projects.append(self.store.project_bundle(project["id"]))
        return {
            "projects": projects,
            "counts": {key: len(value) for key, value in db.items()},
        }

    def create_project(self, name: str, description: str = "") -> dict:
        project = self.store.create_project(name, "sic_gan_switching", description)
        self.store.save_config(default_sic_gan_config(project["id"]))
        return self.store.project_bundle(project["id"])

    def import_dataset(self, project_id: str, filename: str, content: str) -> dict:
        plugin = plugin_for_filename(filename)
        rows = plugin.load_text(content)
        dataset_id = new_id("dataset")
        safe_name = filename.replace("\\", "_").replace("/", "_")
        data_path = self.store.upload_dir / f"{dataset_id}_{safe_name}"
        data_path.write_text(content, encoding="utf-8")
        dataset = {
            "id": dataset_id,
            "project_id": project_id,
            "source_type": plugin.source_type,
            "filename": filename,
            "file_path": str(data_path),
            "rows": len(rows),
            "field_mapping": {
                "time": "time",
                "vgs": "vgs",
                "vds": "vds",
                "ids": "ids",
                "temperature": "temperature",
            },
            "created_at": utcnow(),
        }
        return self.store.save_dataset(dataset)

    def create_run(self, project_id: str, dataset_id: str, parameters: dict, label: str = "") -> dict:
        config = self._config(project_id)
        dataset = self.store.get_dataset(dataset_id)
        if not dataset:
            raise ValueError("Dataset not found.")
        content = Path(dataset["file_path"]).read_text(encoding="utf-8")
        rows = plugin_for_filename(dataset["filename"]).load_text(content)
        metrics = self.feature_plugin.extract(rows, config)
        run = {
            "id": new_id("run"),
            "project_id": project_id,
            "config_id": config["id"],
            "dataset_id": dataset_id,
            "status": "completed",
            "label": label,
            "parameters": self._clean_parameters(parameters),
            "metrics": metrics,
            "chart": self._chart_points(rows),
            "created_at": utcnow(),
            "completed_at": utcnow(),
        }
        return self.store.save_run(run)

    def recommend(self, project_id: str) -> dict:
        config = self._config(project_id)
        runs = self.store.runs_for_project(project_id)
        draft = self.optimizer.recommend(runs, config)
        safety = self.constraints.check(draft, config)
        recommendation = {
            "id": new_id("rec"),
            "project_id": project_id,
            "source_run_ids": [run["id"] for run in runs[-5:]],
            "recommended_parameters": draft["recommended_parameters"],
            "expected_improvement": draft.get("expected_improvement", {}),
            "reasons": draft.get("reasons", []),
            "safety_result": safety,
            "status": "pending_user_confirmation" if safety["passed"] else "rejected_by_safety",
            "created_at": utcnow(),
        }
        return self.store.save_recommendation(recommendation)

    def generate_report(self, project_id: str) -> dict:
        bundle = self.store.project_bundle(project_id)
        if not bundle["project"]:
            raise ValueError("Project not found.")
        html = self.reporter.generate(
            bundle["project"],
            bundle["runs"],
            bundle["recommendations"],
        )
        report_id = new_id("report")
        path = self.store.report_dir / f"{report_id}.html"
        path.write_text(html, encoding="utf-8")
        report = {
            "id": report_id,
            "project_id": project_id,
            "format": "html",
            "path": str(path),
            "url": f"/reports/{report_id}.html",
            "created_at": utcnow(),
        }
        return self.store.save_report(report)

    def load_demo(self) -> dict:
        self.store.reset()
        bundle = self.create_project("SiC/GaN 关断振荡优化演示", "内置样例数据，用于验证 MVP 闭环。")
        project_id = bundle["project"]["id"]
        samples = [
            ("sic_gan_baseline.csv", {"dead_time": 120, "gate_resistance": 4, "drive_voltage": 16, "damping_resistance": 2}, "baseline"),
            ("sic_gan_improved.csv", {"dead_time": 150, "gate_resistance": 6, "drive_voltage": 15, "damping_resistance": 3}, "improved"),
        ]
        for filename, params, label in samples:
            content = (self.sample_dir / filename).read_text(encoding="utf-8")
            dataset = self.import_dataset(project_id, filename, content)
            self.create_run(project_id, dataset["id"], params, label)
        self.recommend(project_id)
        self.generate_report(project_id)
        return self.store.project_bundle(project_id)

    def _config(self, project_id: str) -> dict:
        config = self.store.latest_config(project_id)
        if not config:
            config = self.store.save_config(default_sic_gan_config(project_id))
        return config

    def _clean_parameters(self, parameters: dict) -> dict:
        return {key: float(value) for key, value in parameters.items() if value not in ("", None)}

    def _chart_points(self, rows: list[dict[str, float]]) -> list[dict[str, float]]:
        if len(rows) <= 160:
            sample = rows
        else:
            step = max(1, len(rows) // 160)
            sample = rows[::step]
        return [
            {
                "time": row["time"],
                "vgs": row["vgs"],
                "vds": row["vds"],
                "ids": row["ids"],
            }
            for row in sample
        ]

    def export_json(self) -> str:
        return json.dumps(self.state(), ensure_ascii=False, indent=2)

