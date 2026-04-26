from __future__ import annotations


class HeuristicOptimizerPlugin:
    name = "HeuristicOptimizerPlugin"

    def recommend(self, runs: list[dict], config: dict) -> dict:
        parameter_space = config.get("parameter_space", {})
        if not runs:
            params = {
                name: self._midpoint(bounds)
                for name, bounds in parameter_space.items()
            }
            return {
                "recommended_parameters": params,
                "expected_improvement": {},
                "reasons": ["暂无历史 run，使用参数空间中点作为安全起始建议。"],
            }

        ranked = sorted(runs, key=lambda run: self._score(run.get("metrics", {}), config))
        best = ranked[0]
        metrics = best.get("metrics", {})
        params = dict(best.get("parameters", {}))
        reasons = [f"以表现最好的历史 run 为基准：{best.get('label') or best['id']}。"]

        overshoot = metrics.get("overshoot_ratio", 0)
        settling = metrics.get("settling_time_us", 0)
        risk = metrics.get("risk_level", "low")

        if overshoot > 0.16:
            params["gate_resistance"] = params.get("gate_resistance", self._midpoint(parameter_space["gate_resistance"])) + 1.0
            params["drive_voltage"] = params.get("drive_voltage", self._midpoint(parameter_space["drive_voltage"])) - 0.25
            reasons.append("过冲偏高，建议提高栅极电阻并略降驱动电压。")
        elif overshoot < 0.08 and settling > 1.6:
            params["gate_resistance"] = params.get("gate_resistance", self._midpoint(parameter_space["gate_resistance"])) - 0.5
            reasons.append("过冲余量较好但衰减偏慢，建议小幅降低栅极电阻探索效率边界。")
        else:
            params["dead_time"] = params.get("dead_time", self._midpoint(parameter_space["dead_time"])) + 10.0
            reasons.append("历史指标较均衡，围绕最佳点小步探索死区时间。")

        if settling > 2.0 and "damping_resistance" in parameter_space:
            params["damping_resistance"] = params.get("damping_resistance", self._midpoint(parameter_space["damping_resistance"])) + 0.5
            reasons.append("振荡衰减时间偏长，建议增加阻尼参数。")

        if risk != "low":
            params["drive_voltage"] = params.get("drive_voltage", self._midpoint(parameter_space["drive_voltage"])) - 0.5
            reasons.append("最近最佳结果仍有风险提示，建议保守降低驱动电压。")

        params = {name: self._clamp(round(value, 4), parameter_space[name]) for name, value in params.items() if name in parameter_space}

        return {
            "recommended_parameters": params,
            "expected_improvement": {
                "overshoot_ratio": "-5% to -12%",
                "settling_time_us": "-3% to -10%",
            },
            "reasons": reasons,
        }

    def _score(self, metrics: dict, config: dict) -> float:
        weights = config.get("objective_weights", {})
        overshoot = metrics.get("overshoot_ratio", 0.0)
        settling = metrics.get("settling_time_us", 0.0) / 5.0
        loss = metrics.get("switching_loss_estimate", 0.0) / 0.1
        risk_penalty = {"low": 0, "medium": 0.8, "high": 2.0}.get(metrics.get("risk_level"), 0.5)
        return (
            overshoot * weights.get("overshoot_ratio", 0.4)
            + settling * weights.get("settling_time_us", 0.3)
            + loss * weights.get("switching_loss_estimate", 0.3)
            + risk_penalty
        )

    def _midpoint(self, bounds: dict) -> float:
        return (float(bounds["min"]) + float(bounds["max"])) / 2

    def _clamp(self, value: float, bounds: dict) -> float:
        return min(max(value, float(bounds["min"])), float(bounds["max"]))

