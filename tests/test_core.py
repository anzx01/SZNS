from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lab_mvp.constraints import SiCGaNConstraintPlugin
from lab_mvp.data_plugins import CSVDataSourcePlugin
from lab_mvp.features import SiCGaNFeaturePlugin
from lab_mvp.models import default_sic_gan_config
from lab_mvp.orchestrator import ExperimentOrchestrator
from lab_mvp.storage import JsonStore


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


if __name__ == "__main__":
    unittest.main()

