"""Tests for external plugin examples and the CLI validation tool."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lab_mvp.external_plugins import discover_external_plugins
from lab_mvp.models import default_sic_gan_config, default_track_insulation_config
from lab_mvp.plugins import validate_package
from lab_mvp.plugins.__main__ import main as cli_main
from lab_mvp.storage import JsonStore
from lab_mvp.orchestrator import ExperimentOrchestrator


PLUGINS_DIR = ROOT / "plugins"


class SiCGaNRmsFeaturePluginTest(unittest.TestCase):
    def _instance(self):
        packages = discover_external_plugins(PLUGINS_DIR)
        for pkg in packages:
            if pkg.spec.name == "SiCGaNRmsFeaturePlugin" and pkg.instance is not None:
                return pkg.instance
        self.fail("SiCGaNRmsFeaturePlugin not found or failed to load")

    def test_extract_returns_expected_keys(self) -> None:
        plugin = self._instance()
        rows = [
            {"time": 0.0, "vds": 720.0, "ids": 40.0},
            {"time": 1e-7, "vds": 950.0, "ids": 30.0},
            {"time": 2e-7, "vds": 810.0, "ids": 15.0},
        ]
        result = plugin.extract(rows, {})

        self.assertIn("vds_rms", result)
        self.assertIn("ids_rms", result)
        self.assertIn("peak_instantaneous_power_w", result)
        self.assertIn("energy_loss_j", result)
        self.assertIn("estimated_temp_rise_k", result)

    def test_extract_rms_values_are_positive(self) -> None:
        plugin = self._instance()
        rows = [{"time": float(i) * 1e-7, "vds": 720.0 + i * 5, "ids": 40.0 - i} for i in range(5)]
        result = plugin.extract(rows, {})

        self.assertGreater(result["vds_rms"], 0)
        self.assertGreater(result["ids_rms"], 0)
        self.assertGreater(result["peak_instantaneous_power_w"], 0)

    def test_extract_empty_rows_returns_empty(self) -> None:
        plugin = self._instance()
        result = plugin.extract([], {})
        self.assertEqual(result, {})


class TrackAgingModelPluginTest(unittest.TestCase):
    def _instance(self):
        packages = discover_external_plugins(PLUGINS_DIR)
        for pkg in packages:
            if pkg.spec.name == "TrackAgingModelPlugin" and pkg.instance is not None:
                return pkg.instance
        self.fail("TrackAgingModelPlugin not found or failed to load")

    def test_fast_mode_produces_12_rows(self) -> None:
        plugin = self._instance()
        config = default_track_insulation_config("proj")
        rows = plugin.simulate(
            {"test_voltage": 500, "detection_period": 6, "alarm_threshold": 2},
            config,
        )
        self.assertEqual(len(rows), 12)

    def test_high_fidelity_produces_48_rows(self) -> None:
        plugin = self._instance()
        config = default_track_insulation_config("proj")
        rows = plugin.simulate(
            {"test_voltage": 500, "detection_period": 6, "alarm_threshold": 2},
            config,
            mode="high_fidelity",
        )
        self.assertEqual(len(rows), 48)

    def test_rows_contain_required_signal_keys(self) -> None:
        plugin = self._instance()
        config = default_track_insulation_config("proj")
        rows = plugin.simulate(
            {"test_voltage": 500, "detection_period": 6, "alarm_threshold": 2},
            config,
        )
        for key in ("time", "voltage", "current", "humidity", "temperature"):
            self.assertIn(key, rows[0])

    def test_resistance_degrades_over_time(self) -> None:
        from lab_mvp.features import TrackInsulationFeaturePlugin

        plugin = self._instance()
        config = default_track_insulation_config("proj")
        rows = plugin.simulate(
            {"test_voltage": 500, "detection_period": 6, "alarm_threshold": 2},
            config,
            mode="high_fidelity",
        )
        metrics = TrackInsulationFeaturePlugin().extract(rows, config)
        self.assertIn("min_insulation_mohm", metrics)
        self.assertIn("degradation_index", metrics)


class CsvReportPluginTest(unittest.TestCase):
    def _instance(self):
        packages = discover_external_plugins(PLUGINS_DIR)
        for pkg in packages:
            if pkg.spec.name == "CsvReportPlugin" and pkg.instance is not None:
                return pkg.instance
        self.fail("CsvReportPlugin not found or failed to load")

    def _minimal_project(self):
        return {"name": "测试项目", "experiment_type": "sic_gan_switching", "updated_at": "2026-01-01T00:00:00"}

    def test_generate_returns_string(self) -> None:
        plugin = self._instance()
        output = plugin.generate(self._minimal_project(), [], [], None, None, None)
        self.assertIsInstance(output, str)
        self.assertIn("# 项目,", output)
        self.assertIn("# 实验类型,", output)

    def test_generate_includes_run_data(self) -> None:
        plugin = self._instance()
        runs = [
            {"id": "run_1", "label": "基线", "source_type": "imported", "created_at": "2026-01-01",
             "metrics": {"max_vds": 950.0, "risk_level": "medium"}},
        ]
        output = plugin.generate(self._minimal_project(), runs, [])

        self.assertIn("## Runs", output)
        self.assertIn("run_1", output)
        self.assertIn("基线", output)
        self.assertIn("max_vds", output)

    def test_generate_includes_recommendations(self) -> None:
        plugin = self._instance()
        recs = [
            {"id": "rec_1", "optimizer": "heuristic", "created_at": "2026-01-01",
             "safety_result": {"passed": True}, "decision": "accepted",
             "recommended_parameters": {"dead_time": 140}},
        ]
        output = plugin.generate(self._minimal_project(), [], recs)

        self.assertIn("## 推荐记录", output)
        self.assertIn("rec_1", output)
        self.assertIn("heuristic", output)

    def test_generate_includes_events(self) -> None:
        plugin = self._instance()
        events = [{"created_at": "2026-01-01", "type": "run.completed", "message": "完成"}]
        output = plugin.generate(self._minimal_project(), [], [], events=events)

        self.assertIn("## 事件日志", output)
        self.assertIn("run.completed", output)


class PluginCatalogCoversNewPackagesTest(unittest.TestCase):
    def test_catalog_contains_new_example_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir))
            orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data", PLUGINS_DIR)
            names = {p["name"] for p in orchestrator.plugin_catalog()}

            self.assertIn("SiCGaNRmsFeaturePlugin", names)
            self.assertIn("TrackAgingModelPlugin", names)
            self.assertIn("CsvReportPlugin", names)


class ValidatePackageTest(unittest.TestCase):
    def test_valid_optimizer_package_passes(self) -> None:
        result = validate_package(PLUGINS_DIR / "conservative_optimizer")
        self.assertTrue(result.ok, result.summary())
        self.assertEqual(result.info.get("type"), "optimizer")

    def test_valid_feature_package_passes(self) -> None:
        result = validate_package(PLUGINS_DIR / "sic_gan_rms_feature")
        self.assertTrue(result.ok, result.summary())

    def test_valid_model_package_passes(self) -> None:
        result = validate_package(PLUGINS_DIR / "track_aging_model")
        self.assertTrue(result.ok, result.summary())

    def test_valid_report_package_passes(self) -> None:
        result = validate_package(PLUGINS_DIR / "csv_report")
        self.assertTrue(result.ok, result.summary())

    def test_nonexistent_path_fails(self) -> None:
        result = validate_package("/nonexistent/path/to/plugin")
        self.assertFalse(result.ok)
        self.assertTrue(any("不存在" in e or "not found" in e.lower() for e in result.errors))

    def test_missing_plugin_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_package(temp_dir)
        self.assertFalse(result.ok)
        self.assertTrue(any("plugin.json" in e for e in result.errors))

    def test_invalid_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "plugin.json").write_text("{not json}", encoding="utf-8")
            result = validate_package(temp_dir)
        self.assertFalse(result.ok)

    def test_unsupported_type_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "plugin.json").write_text(
                json.dumps({
                    "id": "test:X", "name": "X", "type": "unknown_type",
                    "entrypoint": "plugin:X",
                }),
                encoding="utf-8",
            )
            result = validate_package(temp_dir)
        self.assertFalse(result.ok)
        self.assertTrue(any("不支持" in e for e in result.errors))

    def test_missing_required_method_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "plugin.json").write_text(
                json.dumps({
                    "id": "optimizer:Bad", "name": "Bad", "type": "optimizer",
                    "entrypoint": "plugin:Bad",
                }),
                encoding="utf-8",
            )
            (Path(temp_dir) / "plugin.py").write_text("class Bad:\n    pass\n", encoding="utf-8")
            result = validate_package(temp_dir)
        self.assertFalse(result.ok)
        self.assertTrue(any("recommend" in e for e in result.errors))

    def test_data_source_warns_if_no_file_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "plugin.json").write_text(
                json.dumps({
                    "id": "data_source:DS", "name": "DS", "type": "data_source",
                    "entrypoint": "plugin:DS",
                }),
                encoding="utf-8",
            )
            (Path(temp_dir) / "plugin.py").write_text(
                "class DS:\n"
                "    def load_text(self, content, signals, field_mapping): return []\n"
                "    def preview_text(self, *args, **kwargs): return {}\n",
                encoding="utf-8",
            )
            result = validate_package(temp_dir)
        self.assertTrue(result.ok)
        self.assertTrue(any("file_extensions" in w for w in result.warnings))


class CliMainTest(unittest.TestCase):
    def test_validate_command_exits_0_for_valid_package(self) -> None:
        code = cli_main(["validate", str(PLUGINS_DIR / "conservative_optimizer")])
        self.assertEqual(code, 0)

    def test_validate_command_exits_1_for_invalid_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            code = cli_main(["validate", temp_dir])
        self.assertEqual(code, 1)

    def test_list_command_exits_0_for_plugins_dir(self) -> None:
        code = cli_main(["list", str(PLUGINS_DIR)])
        self.assertEqual(code, 0)

    def test_list_command_exits_1_for_nonexistent_dir(self) -> None:
        code = cli_main(["list", "/nonexistent/plugins"])
        self.assertEqual(code, 1)

    def test_no_args_exits_0_with_help(self) -> None:
        code = cli_main([])
        self.assertEqual(code, 0)

    def test_unknown_command_exits_2(self) -> None:
        code = cli_main(["unknown_cmd"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
