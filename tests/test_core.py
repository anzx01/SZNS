from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lab_mvp.constraints import SiCGaNConstraintPlugin, TrackInsulationConstraintPlugin
from lab_mvp.data_plugins import CSVDataSourcePlugin
from lab_mvp.experiments import csv_template
from lab_mvp.features import SiCGaNFeaturePlugin, TrackInsulationFeaturePlugin
from lab_mvp.models import default_sic_gan_config, default_track_insulation_config
from lab_mvp.optimizer import BayesianOptimizerPlugin
from lab_mvp.orchestrator import ExperimentOrchestrator
from lab_mvp.storage import JsonStore
from lab_mvp.twins import SiCGaNDigitalTwinPlugin, TrackInsulationDigitalTwinPlugin


class CoreFlowTest(unittest.TestCase):
    def test_csv_feature_extraction(self) -> None:
        content = (ROOT / "sample_data" / "sic_gan_baseline.csv").read_text(encoding="utf-8")
        rows = CSVDataSourcePlugin().load_text(content)
        config = default_sic_gan_config("project_test")
        metrics = SiCGaNFeaturePlugin().extract(rows, config)

        self.assertGreater(metrics["max_vds"], 850)
        self.assertGreater(metrics["overshoot_ratio"], 0.1)
        self.assertEqual(metrics["risk_level"], "medium")

    def test_constraint_rejects_dangerous_combination(self) -> None:
        config = default_sic_gan_config("project_test")
        recommendation = {
            "recommended_parameters": {
                "dead_time": 70,
                "gate_resistance": 2,
                "drive_voltage": 17.5,
                "damping_resistance": 2,
            }
        }
        result = SiCGaNConstraintPlugin().check(recommendation, config)

        self.assertFalse(result["passed"])
        self.assertTrue(result["reasons"])

    def test_demo_flow_creates_closed_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.load_demo()

            self.assertEqual(len(bundle["runs"]), 2)
            self.assertEqual(len(bundle["recommendations"]), 1)
            self.assertEqual(len(bundle["reports"]), 1)
            self.assertTrue(Path(bundle["reports"][0]["path"]).exists())

    def test_bayesian_optimizer_returns_safe_parameter_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.load_demo()
            recommendation = orchestrator.recommend(bundle["project"]["id"], "bayesian")

            self.assertEqual(recommendation["optimizer"], BayesianOptimizerPlugin.name)
            self.assertIn("dead_time", recommendation["recommended_parameters"])
            self.assertTrue(recommendation["safety_result"]["passed"])

    def test_config_update_creates_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.load_demo()
            project_id = bundle["project"]["id"]
            old_config_id = bundle["config"]["id"]
            patch = {
                "parameter_space": bundle["config"]["parameter_space"],
                "safety_limits": {**bundle["config"]["safety_limits"], "max_vds": 850},
                "objective_weights": bundle["config"]["objective_weights"],
            }
            updated = orchestrator.update_config(project_id, patch)

            self.assertNotEqual(old_config_id, updated["config"]["id"])
            self.assertEqual(updated["config"]["safety_limits"]["max_vds"], 850.0)

    def test_track_feature_extraction(self) -> None:
        content = (ROOT / "sample_data" / "track_insulation_baseline.csv").read_text(encoding="utf-8")
        rows = CSVDataSourcePlugin().load_text(content, ("time", "voltage", "current"))
        config = default_track_insulation_config("project_track")
        metrics = TrackInsulationFeaturePlugin().extract(rows, config)

        self.assertLess(metrics["min_insulation_mohm"], 1.0)
        self.assertGreater(metrics["max_leakage_ma"], 0.5)
        self.assertEqual(metrics["risk_level"], "high")

    def test_track_constraint_rejects_high_voltage(self) -> None:
        config = default_track_insulation_config("project_track")
        recommendation = {
            "recommended_parameters": {
                "test_voltage": 1100,
                "detection_period": 6,
                "alarm_threshold": 2,
            }
        }
        result = TrackInsulationConstraintPlugin().check(recommendation, config)

        self.assertFalse(result["passed"])
        self.assertTrue(result["reasons"])

    def test_track_demo_uses_same_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.load_track_demo()

            self.assertEqual(bundle["project"]["experiment_type"], "track_insulation")
            self.assertEqual(bundle["manifest"]["type"], "track_insulation")
            self.assertEqual(len(bundle["runs"]), 2)
            self.assertIn("min_insulation_mohm", bundle["runs"][0]["metrics"])
            self.assertEqual(len(bundle["recommendations"]), 1)

    def test_state_exposes_experiment_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            state = orchestrator.state()

            manifest_types = {manifest["type"] for manifest in state["experiments"]}
            self.assertIn("sic_gan_switching", manifest_types)
            self.assertIn("track_insulation", manifest_types)

    def test_csv_template_is_manifest_driven(self) -> None:
        sic_template = csv_template("sic_gan_switching")
        track_template = csv_template("track_insulation")

        self.assertTrue(sic_template.startswith("time,vgs,vds,ids,temperature"))
        self.assertTrue(track_template.startswith("time,voltage,current,humidity,temperature"))

    def test_dataset_preview_reports_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.create_project("track", experiment_type="track_insulation")
            content = "time,vds,ids\n0,720,40\n"
            preview = orchestrator.preview_dataset(bundle["project"]["id"], "bad.csv", content)

            self.assertFalse(preview["valid"])
            self.assertIn("voltage", preview["missing"])
            self.assertIn("current", preview["missing"])

    def test_dataset_preview_accepts_track_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.create_project("track", experiment_type="track_insulation")
            preview = orchestrator.preview_dataset(
                bundle["project"]["id"],
                "track.csv",
                csv_template("track_insulation"),
            )

            self.assertTrue(preview["valid"])
            self.assertEqual(preview["rows"], 1)

    def test_field_mapping_allows_alias_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.create_project("sic", experiment_type="sic_gan_switching")
            content = "t,V_DS,Idrain,gate_voltage\n0,720,40,15\n0.1,810,20,0\n"
            preview = orchestrator.preview_dataset(bundle["project"]["id"], "alias.csv", content)

            self.assertTrue(preview["valid"])
            self.assertEqual(preview["field_mapping"]["vds"], "V_DS")
            dataset = orchestrator.import_dataset(
                bundle["project"]["id"],
                "alias.csv",
                content,
                preview["field_mapping"],
            )
            run = orchestrator.create_run(
                bundle["project"]["id"],
                dataset["id"],
                {"dead_time": 120, "gate_resistance": 4, "drive_voltage": 15, "damping_resistance": 2},
                "alias",
            )

            self.assertIn("max_vds", run["metrics"])
            self.assertEqual(dataset["field_mapping"]["ids"], "Idrain")

    def test_experiment_events_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.load_track_demo()
            event_types = {event["type"] for event in bundle["events"]}

            self.assertIn("project.created", event_types)
            self.assertIn("dataset.imported", event_types)
            self.assertIn("run.completed", event_types)
            self.assertIn("recommendation.created", event_types)
            self.assertIn("report.generated", event_types)

    def test_sic_gan_digital_twin_generates_feature_ready_rows(self) -> None:
        config = default_sic_gan_config("project_sic")
        rows = SiCGaNDigitalTwinPlugin().simulate(
            {"dead_time": 140, "gate_resistance": 5, "drive_voltage": 15, "damping_resistance": 2},
            config,
        )
        metrics = SiCGaNFeaturePlugin().extract(rows, config)

        self.assertGreater(len(rows), 20)
        self.assertIn("vds", rows[0])
        self.assertGreater(metrics["max_vds"], 720)

    def test_track_digital_twin_generates_feature_ready_rows(self) -> None:
        config = default_track_insulation_config("project_track")
        rows = TrackInsulationDigitalTwinPlugin().simulate(
            {"test_voltage": 500, "detection_period": 6, "alarm_threshold": 2},
            config,
        )
        metrics = TrackInsulationFeaturePlugin().extract(rows, config)

        self.assertEqual(len(rows), 12)
        self.assertIn("current", rows[0])
        self.assertIn("min_insulation_mohm", metrics)

    def test_simulated_run_enters_closed_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.create_project("sic", experiment_type="sic_gan_switching")
            run = orchestrator.simulate_run(
                bundle["project"]["id"],
                {"dead_time": 140, "gate_resistance": 5, "drive_voltage": 15, "damping_resistance": 2},
                "sim",
            )
            updated = store.project_bundle(bundle["project"]["id"])
            event_types = {event["type"] for event in updated["events"]}

            self.assertEqual(run["source_type"], "simulation")
            self.assertIn("max_vds", run["metrics"])
            self.assertIn("simulation.completed", event_types)

    def test_recommendation_can_be_simulated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.load_demo()
            recommendation = bundle["recommendations"][-1]
            run = orchestrator.simulate_recommendation(
                bundle["project"]["id"],
                recommendation["id"],
                "high_fidelity",
            )

            self.assertEqual(run["recommendation_id"], recommendation["id"])
            self.assertEqual(run["model_mode"], "high_fidelity")
            self.assertGreater(len(run["chart"]), 40)

    def test_model_calibration_creates_config_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            bundle = orchestrator.load_demo()
            old_config_id = bundle["config"]["id"]
            updated = orchestrator.calibrate_model(bundle["project"]["id"])

            self.assertNotEqual(old_config_id, updated["config"]["id"])
            self.assertTrue(updated["config"]["model_calibration"])

    def test_plugin_catalog_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")
            catalog = orchestrator.plugin_catalog()
            names = {plugin["name"] for plugin in catalog}

            self.assertIn("DataPreprocessorPlugin", names)
            self.assertIn("SiCGaNDigitalTwinPlugin", names)


if __name__ == "__main__":
    unittest.main()
