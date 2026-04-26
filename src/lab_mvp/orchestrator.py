from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from .constraints import SiCGaNConstraintPlugin, TrackInsulationConstraintPlugin
from .data_plugins import plugin_for_filename
from .experiments import all_experiment_manifests, csv_template, experiment_manifest
from .features import SiCGaNFeaturePlugin, TrackInsulationFeaturePlugin
from .models import default_config_for, new_id, utcnow
from .optimizer import BayesianOptimizerPlugin, HeuristicOptimizerPlugin
from .preprocessing import DataPreprocessorPlugin
from .reports import HTMLReportPlugin
from .storage import JsonStore
from .twins import SiCGaNDigitalTwinPlugin, TrackInsulationDigitalTwinPlugin


class ExperimentOrchestrator:
    def __init__(self, store: JsonStore, sample_dir: Path):
        self.store = store
        self.sample_dir = sample_dir
        self.feature_plugins = {
            "sic_gan_switching": SiCGaNFeaturePlugin(),
            "track_insulation": TrackInsulationFeaturePlugin(),
        }
        self.model_plugins = {
            "sic_gan_switching": SiCGaNDigitalTwinPlugin(),
            "track_insulation": TrackInsulationDigitalTwinPlugin(),
        }
        self.optimizers = {
            "heuristic": HeuristicOptimizerPlugin(),
            "bayesian": BayesianOptimizerPlugin(),
        }
        self.preprocessor = DataPreprocessorPlugin()
        self.constraint_plugins = {
            "sic_gan_switching": SiCGaNConstraintPlugin(),
            "track_insulation": TrackInsulationConstraintPlugin(),
        }
        self.reporter = HTMLReportPlugin()

    def state(self) -> dict:
        db = self.store.all()
        projects = []
        for project in db["projects"]:
            projects.append(self._bundle(project["id"]))
        return {
            "projects": projects,
            "experiments": all_experiment_manifests(),
            "plugin_catalog": self.plugin_catalog(),
            "counts": {key: len(value) for key, value in db.items()},
        }

    def plugin_catalog(self) -> list[dict]:
        catalog = [
            {"name": self.preprocessor.name, "type": "data_processing", "status": "active"},
            {"name": "CSVDataSourcePlugin", "type": "data_source", "status": "active"},
            {"name": "JSONDataSourcePlugin", "type": "data_source", "status": "active"},
            {"name": "HTMLReportPlugin", "type": "report", "status": "active"},
        ]
        for optimizer in self.optimizers.values():
            catalog.append({"name": optimizer.name, "type": "optimizer", "status": "active"})
        for manifest in all_experiment_manifests():
            for role, name in manifest.get("plugins", {}).items():
                catalog.append({
                    "name": name,
                    "type": role,
                    "experiment_type": manifest["type"],
                    "status": "active",
                })
        return catalog

    def create_project(
        self,
        name: str,
        description: str = "",
        experiment_type: str = "sic_gan_switching",
    ) -> dict:
        experiment_manifest(experiment_type)
        project = self.store.create_project(name, experiment_type, description)
        self.store.save_config(default_config_for(experiment_type, project["id"]))
        self._log_event(
            project["id"],
            "project.created",
            f"创建项目 {name}",
            {"experiment_type": experiment_type},
        )
        return self._bundle(project["id"])

    def csv_template(self, experiment_type: str) -> str:
        return csv_template(experiment_type)

    def update_config(self, project_id: str, patch: dict) -> dict:
        updated = self._save_config_version(project_id, self._config(project_id), patch)
        self._log_event(project_id, "config.updated", "保存了新的配置版本", {"config_id": updated["config"]["id"]})
        return updated

    def _save_config_version(self, project_id: str, current: dict, patch: dict) -> dict:
        config = deepcopy(current)
        config["id"] = new_id("config")
        config["parent_config_id"] = current["id"]
        config["created_at"] = utcnow()
        config["updated_at"] = utcnow()

        for section in ("parameter_space", "safety_limits", "objective_weights", "model_calibration"):
            if section in patch:
                config[section] = patch[section]

        self._validate_config(config)
        self.store.save_config(config)
        return self._bundle(project_id)

    def preview_dataset(
        self,
        project_id: str,
        filename: str,
        content: str,
        field_mapping: dict[str, str] | None = None,
    ) -> dict:
        manifest = self._manifest(project_id)
        plugin = plugin_for_filename(filename)
        preview = plugin.preview_text(
            content,
            manifest["required_signals"],
            manifest.get("optional_signals", ()),
            field_mapping,
            manifest.get("field_aliases", {}),
        )
        preview["quality"] = self.preprocessor.summarize(preview.get("preview_rows", []), manifest)
        preview["experiment_type"] = self.store.get_project(project_id)["experiment_type"]
        preview["filename"] = filename
        return preview

    def import_dataset(
        self,
        project_id: str,
        filename: str,
        content: str,
        field_mapping: dict[str, str] | None = None,
    ) -> dict:
        manifest = self._manifest(project_id)
        plugin = plugin_for_filename(filename)
        preview = self.preview_dataset(project_id, filename, content, field_mapping)
        if not preview["valid"]:
            raise ValueError("; ".join(preview["errors"]))
        rows = plugin.load_text(content, manifest["required_signals"], preview["field_mapping"])
        _, quality = self.preprocessor.process(rows, manifest)
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
            "field_mapping": preview["field_mapping"],
            "fieldnames": preview["fieldnames"],
            "quality": quality,
            "created_at": utcnow(),
        }
        saved = self.store.save_dataset(dataset)
        self._log_event(
            project_id,
            "dataset.imported",
            f"导入数据集 {filename}",
            {"dataset_id": dataset_id, "rows": len(rows), "field_mapping": preview["field_mapping"]},
        )
        return saved

    def create_run(self, project_id: str, dataset_id: str, parameters: dict, label: str = "") -> dict:
        config = self._config(project_id)
        dataset = self.store.get_dataset(dataset_id)
        if not dataset:
            raise ValueError("Dataset not found.")
        content = Path(dataset["file_path"]).read_text(encoding="utf-8")
        manifest = self._manifest(project_id)
        rows = plugin_for_filename(dataset["filename"]).load_text(
            content,
            manifest["required_signals"],
            dataset.get("field_mapping"),
        )
        rows, preprocessing = self.preprocessor.process(rows, manifest)
        metrics = self._feature_plugin(project_id).extract(rows, config)
        run = {
            "id": new_id("run"),
            "project_id": project_id,
            "config_id": config["id"],
            "dataset_id": dataset_id,
            "status": "completed",
            "label": label,
            "parameters": self._clean_parameters(parameters),
            "preprocessing": preprocessing,
            "metrics": metrics,
            "chart": self._chart_points(rows, manifest["chart_series"]),
            "created_at": utcnow(),
            "completed_at": utcnow(),
        }
        saved = self.store.save_run(run)
        self._log_event(
            project_id,
            "run.completed",
            f"完成 run {label or run['id']}",
            {"run_id": run["id"], "dataset_id": dataset_id, "risk_level": metrics.get("risk_level")},
        )
        return saved

    def simulate_run(
        self,
        project_id: str,
        parameters: dict,
        label: str = "",
        mode: str = "fast",
        recommendation_id: str | None = None,
    ) -> dict:
        config = self._config(project_id)
        manifest = self._manifest(project_id)
        clean_params = self._clean_parameters(parameters)
        model_mode = mode if mode in {"fast", "high_fidelity"} else "fast"
        rows = self._model_plugin(project_id).simulate(clean_params, config, model_mode)
        rows, preprocessing = self.preprocessor.process(rows, manifest)
        metrics = self._feature_plugin(project_id).extract(rows, config)
        run = {
            "id": new_id("run"),
            "project_id": project_id,
            "config_id": config["id"],
            "dataset_id": None,
            "source_type": "simulation",
            "model": self._model_plugin(project_id).name,
            "model_mode": model_mode,
            "recommendation_id": recommendation_id,
            "status": "completed",
            "label": label or "simulation",
            "parameters": clean_params,
            "preprocessing": preprocessing,
            "metrics": metrics,
            "chart": self._chart_points(rows, manifest["chart_series"]),
            "created_at": utcnow(),
            "completed_at": utcnow(),
        }
        saved = self.store.save_run(run)
        self._log_event(
            project_id,
            "simulation.completed",
            f"完成仿真 run {run['label']}",
            {"run_id": run["id"], "model": run["model"], "mode": model_mode, "risk_level": metrics.get("risk_level")},
        )
        return saved

    def simulate_recommendation(
        self,
        project_id: str,
        recommendation_id: str | None = None,
        mode: str = "fast",
    ) -> dict:
        recommendation = self.store.get_recommendation(recommendation_id) if recommendation_id else None
        if not recommendation:
            recommendations = self.store.recommendations_for_project(project_id)
            if not recommendations:
                raise ValueError("No recommendation available.")
            recommendation = recommendations[-1]
        run = self.simulate_run(
            project_id,
            recommendation["recommended_parameters"],
            f"verify-{recommendation['id'][-6:]}",
            mode,
            recommendation["id"],
        )
        self._log_event(
            project_id,
            "recommendation.simulated",
            "仿真验证推荐参数",
            {"recommendation_id": recommendation["id"], "run_id": run["id"], "mode": mode},
        )
        return run

    def calibrate_model(self, project_id: str) -> dict:
        real_runs = [
            run for run in self.store.runs_for_project(project_id)
            if run.get("source_type") != "simulation" and run.get("parameters")
        ]
        if not real_runs:
            raise ValueError("需要至少一个真实/导入 run 才能校准模型。")
        latest = real_runs[-1]
        config = self._config(project_id)
        simulated_rows = self._model_plugin(project_id).simulate(latest["parameters"], config, "fast")
        simulated_metrics = self._feature_plugin(project_id).extract(simulated_rows, config)
        calibration = self._calibration_for_metrics(
            self.store.get_project(project_id)["experiment_type"],
            latest["metrics"],
            simulated_metrics,
        )
        updated = self._save_config_version(
            project_id,
            config,
            {
                "parameter_space": deepcopy(config.get("parameter_space", {})),
                "safety_limits": deepcopy(config.get("safety_limits", {})),
                "objective_weights": deepcopy(config.get("objective_weights", {})),
                "model_calibration": calibration,
            },
        )
        self._log_event(
            project_id,
            "model.calibrated",
            "根据最新导入 run 在线校准模型",
            {"source_run_id": latest["id"], "model_calibration": calibration},
        )
        return updated

    def recommend(self, project_id: str, optimizer_name: str = "bayesian") -> dict:
        config = self._config(project_id)
        runs = self.store.runs_for_project(project_id)
        optimizer_key = optimizer_name if optimizer_name in self.optimizers else "bayesian"
        draft = self.optimizers[optimizer_key].recommend(runs, config)
        safety = self._constraint_plugin(project_id).check(draft, config)
        recommendation = {
            "id": new_id("rec"),
            "project_id": project_id,
            "config_id": config["id"],
            "optimizer": draft.get("optimizer") or self.optimizers[optimizer_key].name,
            "source_run_ids": [run["id"] for run in runs[-5:]],
            "recommended_parameters": draft["recommended_parameters"],
            "expected_improvement": draft.get("expected_improvement", {}),
            "reasons": draft.get("reasons", []),
            "safety_result": safety,
            "status": "pending_user_confirmation" if safety["passed"] else "rejected_by_safety",
            "created_at": utcnow(),
        }
        saved = self.store.save_recommendation(recommendation)
        self._log_event(
            project_id,
            "recommendation.created",
            "生成参数推荐",
            {
                "recommendation_id": recommendation["id"],
                "optimizer": recommendation["optimizer"],
                "status": recommendation["status"],
            },
        )
        return saved

    def generate_report(self, project_id: str) -> dict:
        bundle = self._bundle(project_id)
        if not bundle["project"]:
            raise ValueError("Project not found.")
        html = self.reporter.generate(
            bundle["project"],
            bundle["runs"],
            bundle["recommendations"],
            bundle.get("config"),
            bundle.get("manifest"),
            bundle.get("events", []),
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
        saved = self.store.save_report(report)
        self._log_event(project_id, "report.generated", "生成 HTML 报告", {"report_id": report_id})
        return saved

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
        self.recommend(project_id, "bayesian")
        self.generate_report(project_id)
        return self._bundle(project_id)

    def load_track_demo(self) -> dict:
        bundle = self.create_project(
            "轨道绝缘检测演示",
            "第二实验类型样例，用于验证插件化扩展能力。",
            "track_insulation",
        )
        project_id = bundle["project"]["id"]
        samples = [
            ("track_insulation_baseline.csv", {"test_voltage": 500, "detection_period": 6, "alarm_threshold": 2.0}, "humid-baseline"),
            ("track_insulation_improved.csv", {"test_voltage": 450, "detection_period": 4, "alarm_threshold": 2.5}, "stabilized"),
        ]
        for filename, params, label in samples:
            content = (self.sample_dir / filename).read_text(encoding="utf-8")
            dataset = self.import_dataset(project_id, filename, content)
            self.create_run(project_id, dataset["id"], params, label)
        self.recommend(project_id, "bayesian")
        self.generate_report(project_id)
        return self._bundle(project_id)

    def _config(self, project_id: str) -> dict:
        config = self.store.latest_config(project_id)
        if not config:
            project = self.store.get_project(project_id)
            experiment_type = project["experiment_type"] if project else "sic_gan_switching"
            config = self.store.save_config(default_config_for(experiment_type, project_id))
        return config

    def _bundle(self, project_id: str) -> dict:
        bundle = self.store.project_bundle(project_id)
        if bundle["project"]:
            bundle["manifest"] = experiment_manifest(bundle["project"]["experiment_type"])
        return bundle

    def _manifest(self, project_id: str) -> dict:
        project = self.store.get_project(project_id)
        if not project:
            raise ValueError("Project not found.")
        return experiment_manifest(project["experiment_type"])

    def _feature_plugin(self, project_id: str):
        project = self.store.get_project(project_id)
        if not project:
            raise ValueError("Project not found.")
        return self.feature_plugins[project["experiment_type"]]

    def _model_plugin(self, project_id: str):
        project = self.store.get_project(project_id)
        if not project:
            raise ValueError("Project not found.")
        return self.model_plugins[project["experiment_type"]]

    def _constraint_plugin(self, project_id: str):
        project = self.store.get_project(project_id)
        if not project:
            raise ValueError("Project not found.")
        return self.constraint_plugins[project["experiment_type"]]

    def _calibration_for_metrics(self, experiment_type: str, actual: dict, simulated: dict) -> dict:
        if experiment_type == "track_insulation":
            resistance_scale = self._bounded_ratio(
                actual.get("min_insulation_mohm"),
                simulated.get("min_insulation_mohm"),
                0.4,
                2.5,
            )
            return {
                "resistance_scale": round(resistance_scale, 5),
                "source": "latest_run_ratio",
            }
        max_vds_ratio = self._bounded_ratio(actual.get("max_vds"), simulated.get("max_vds"), 0.75, 1.35)
        max_ids_ratio = self._bounded_ratio(actual.get("max_ids"), simulated.get("max_ids"), 0.75, 1.35)
        return {
            "overshoot_scale": round(max_vds_ratio, 5),
            "ids_scale": round(max_ids_ratio, 5),
            "source": "latest_run_ratio",
        }

    def _bounded_ratio(self, numerator, denominator, low: float, high: float) -> float:
        if numerator is None or denominator in (None, 0):
            return 1.0
        return min(max(float(numerator) / max(float(denominator), 1e-9), low), high)

    def _log_event(self, project_id: str, event_type: str, message: str, details: dict | None = None) -> dict:
        return self.store.save_event(
            {
                "id": new_id("event"),
                "project_id": project_id,
                "type": event_type,
                "message": message,
                "details": details or {},
                "created_at": utcnow(),
            }
        )

    def _clean_parameters(self, parameters: dict) -> dict:
        return {key: float(value) for key, value in parameters.items() if value not in ("", None)}

    def _validate_config(self, config: dict) -> None:
        parameter_space = config.get("parameter_space", {})
        if not parameter_space:
            raise ValueError("参数空间不能为空。")
        for name, bounds in parameter_space.items():
            if "min" not in bounds or "max" not in bounds:
                raise ValueError(f"{name} 缺少 min/max。")
            bounds["min"] = float(bounds["min"])
            bounds["max"] = float(bounds["max"])
            if bounds["min"] >= bounds["max"]:
                raise ValueError(f"{name} 的 min 必须小于 max。")
            bounds.setdefault("unit", "")

        limits = config.get("safety_limits", {})
        for name, value in list(limits.items()):
            limits[name] = float(value)
            if limits[name] <= 0:
                raise ValueError(f"{name} 必须大于 0。")

        weights = config.get("objective_weights", {})
        for name, value in list(weights.items()):
            weights[name] = float(value)
            if weights[name] < 0:
                raise ValueError(f"{name} 权重不能为负数。")

    def _chart_points(self, rows: list[dict[str, float]], series: tuple[str, ...]) -> list[dict[str, float]]:
        if len(rows) <= 160:
            sample = rows
        else:
            step = max(1, len(rows) // 160)
            sample = rows[::step]
        return [
            {"time": row["time"], **{name: row[name] for name in series if name in row}}
            for row in sample
        ]

    def export_json(self) -> str:
        return json.dumps(self.state(), ensure_ascii=False, indent=2)
