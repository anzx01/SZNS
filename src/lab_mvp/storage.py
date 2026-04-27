from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import new_id, utcnow


EMPTY_DB = {
    "projects": [],
    "configs": [],
    "datasets": [],
    "runs": [],
    "recommendations": [],
    "reports": [],
    "events": [],
    "plugins": [],
}


class JsonStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "store.json"
        self.upload_dir = self.root / "uploads"
        self.report_dir = self.root / "reports"
        self.upload_dir.mkdir(exist_ok=True)
        self.report_dir.mkdir(exist_ok=True)
        if not self.db_path.exists():
            self._write(EMPTY_DB.copy())

    def all(self) -> dict[str, list[dict[str, Any]]]:
        return self._read()

    def reset(self, preserve_plugins: bool = True) -> None:
        plugins = self._read().get("plugins", []) if preserve_plugins else []
        next_db = {key: [] for key in EMPTY_DB}
        next_db["plugins"] = plugins
        self._write(next_db)

    def create_project(self, name: str, experiment_type: str, description: str = "") -> dict:
        db = self._read()
        project = {
            "id": new_id("project"),
            "name": name,
            "experiment_type": experiment_type,
            "description": description,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        db["projects"].append(project)
        self._write(db)
        return project

    def save_config(self, config: dict) -> dict:
        db = self._read()
        db["configs"] = [item for item in db["configs"] if item["id"] != config["id"]]
        db["configs"].append(config)
        self._write(db)
        return config

    def latest_config(self, project_id: str) -> dict | None:
        configs = [item for item in self._read()["configs"] if item["project_id"] == project_id]
        return configs[-1] if configs else None

    def get_project(self, project_id: str) -> dict | None:
        return self._find("projects", project_id)

    def save_dataset(self, dataset: dict) -> dict:
        db = self._read()
        db["datasets"].append(dataset)
        self._write(db)
        return dataset

    def get_dataset(self, dataset_id: str) -> dict | None:
        return self._find("datasets", dataset_id)

    def save_run(self, run: dict) -> dict:
        db = self._read()
        db["runs"] = [item for item in db["runs"] if item["id"] != run["id"]]
        db["runs"].append(run)
        self._write(db)
        return run

    def runs_for_project(self, project_id: str) -> list[dict]:
        return [item for item in self._read()["runs"] if item["project_id"] == project_id]

    def get_recommendation(self, recommendation_id: str | None) -> dict | None:
        if not recommendation_id:
            return None
        return self._find("recommendations", recommendation_id)

    def recommendations_for_project(self, project_id: str) -> list[dict]:
        return [item for item in self._read()["recommendations"] if item["project_id"] == project_id]

    def save_recommendation(self, recommendation: dict) -> dict:
        db = self._read()
        db["recommendations"] = [
            item for item in db["recommendations"] if item["id"] != recommendation["id"]
        ]
        db["recommendations"].append(recommendation)
        self._write(db)
        return recommendation

    def save_report(self, report: dict) -> dict:
        db = self._read()
        db["reports"].append(report)
        self._write(db)
        return report

    def save_event(self, event: dict) -> dict:
        db = self._read()
        db["events"].append(event)
        self._write(db)
        return event

    def plugin_states(self) -> dict[str, dict]:
        return {item["id"]: item for item in self._read()["plugins"]}

    def save_plugin_state(self, plugin_id: str, loaded: bool) -> dict:
        db = self._read()
        state = {
            "id": plugin_id,
            "loaded": bool(loaded),
            "updated_at": utcnow(),
        }
        db["plugins"] = [item for item in db["plugins"] if item["id"] != plugin_id]
        db["plugins"].append(state)
        self._write(db)
        return state

    def project_bundle(self, project_id: str) -> dict:
        db = self._read()
        project = next((item for item in db["projects"] if item["id"] == project_id), None)
        return {
            "project": project,
            "config": self.latest_config(project_id),
            "datasets": [item for item in db["datasets"] if item["project_id"] == project_id],
            "runs": [item for item in db["runs"] if item["project_id"] == project_id],
            "recommendations": [
                item for item in db["recommendations"] if item["project_id"] == project_id
            ],
            "reports": [item for item in db["reports"] if item["project_id"] == project_id],
            "events": [item for item in db["events"] if item["project_id"] == project_id],
        }

    def _find(self, collection: str, item_id: str) -> dict | None:
        return next((item for item in self._read()[collection] if item["id"] == item_id), None)

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        with self.db_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        for key in EMPTY_DB:
            data.setdefault(key, [])
        return data

    def _write(self, data: dict[str, list[dict[str, Any]]]) -> None:
        tmp = self.db_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        tmp.replace(self.db_path)
