from __future__ import annotations


class ConservativeOptimizerPlugin:
    name = "ConservativeOptimizerPlugin"

    def recommend(self, runs: list[dict], config: dict) -> dict:
        parameter_space = config.get("parameter_space", {})
        params = {
            name: self._conservative_value(name, bounds)
            for name, bounds in parameter_space.items()
        }
        return {
            "recommended_parameters": params,
            "expected_improvement": {
                "risk_margin": "+conservative",
            },
            "optimizer": self.name,
            "reasons": [
                "External plugin package loaded from plugins/conservative_optimizer.",
                "Uses conservative values inside each declared action bound.",
                f"Observed {len(runs)} historical runs before making this recommendation.",
            ],
        }

    def _conservative_value(self, name: str, bounds: dict) -> float:
        low = float(bounds["min"])
        high = float(bounds["max"])
        span = high - low
        if name in {"drive_voltage", "test_voltage"}:
            value = low + span * 0.35
        elif name in {"gate_resistance", "damping_resistance", "alarm_threshold"}:
            value = low + span * 0.65
        else:
            value = low + span * 0.5
        return round(value, 4)
