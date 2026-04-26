from __future__ import annotations

from itertools import product
from math import exp, sqrt


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

        if "test_voltage" in parameter_space:
            return self._recommend_track(parameter_space, metrics, params, reasons)

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

    def _recommend_track(self, parameter_space: dict, metrics: dict, params: dict, reasons: list[str]) -> dict:
        risk = metrics.get("risk_level", "low")
        min_resistance = metrics.get("min_insulation_mohm", 999)
        leakage = metrics.get("max_leakage_ma", 0)

        if risk != "low":
            params["test_voltage"] = params.get("test_voltage", self._midpoint(parameter_space["test_voltage"])) - 50
            params["detection_period"] = params.get("detection_period", self._midpoint(parameter_space["detection_period"])) - 2
            params["alarm_threshold"] = params.get("alarm_threshold", self._midpoint(parameter_space["alarm_threshold"])) + 0.5
            reasons.append("绝缘风险偏高，建议降低测试电压、缩短检测周期并提高报警阈值。")
        elif min_resistance > 4 and leakage < 0.8:
            params["detection_period"] = params.get("detection_period", self._midpoint(parameter_space["detection_period"])) + 2
            reasons.append("绝缘余量较好，建议小幅延长检测周期以降低测试频次。")
        else:
            params["test_voltage"] = params.get("test_voltage", self._midpoint(parameter_space["test_voltage"])) + 25
            reasons.append("指标处于可接受区间，建议小幅提高测试电压探索检测灵敏度。")

        params = {
            name: self._clamp(round(value, 4), parameter_space[name])
            for name, value in params.items()
            if name in parameter_space
        }

        return {
            "recommended_parameters": params,
            "expected_improvement": {
                "degradation_index": "-5% to -10%",
                "detection_confidence": "+3% to +8%",
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


class BayesianOptimizerPlugin:
    """Dependency-free surrogate optimizer for small laboratory datasets.

    This is intentionally modest: it uses an RBF-weighted surrogate and an
    exploration bonus instead of pulling in a numerical optimization stack.
    """

    name = "BayesianOptimizerPlugin"

    def recommend(self, runs: list[dict], config: dict) -> dict:
        parameter_space = config.get("parameter_space", {})
        completed = [
            run for run in runs
            if run.get("parameters") and run.get("metrics") and self._has_declared_params(run, parameter_space)
        ]
        if len(completed) < 2:
            draft = HeuristicOptimizerPlugin().recommend(runs, config)
            draft["reasons"].append("历史样本少于 2 个，贝叶斯式优化回退到启发式建议。")
            draft["optimizer"] = self.name
            return draft

        observations = [
            {
                "params": self._normalize(run["parameters"], parameter_space),
                "raw_params": run["parameters"],
                "score": self._score(run.get("metrics", {}), config),
                "label": run.get("label") or run["id"],
            }
            for run in completed
        ]
        best_observation = min(observations, key=lambda item: item["score"])
        candidates = self._candidate_params(parameter_space, best_observation["raw_params"])
        ranked = []
        for candidate in candidates:
            normalized = self._normalize(candidate, parameter_space)
            predicted_score, uncertainty = self._predict(normalized, observations)
            acquisition = predicted_score - 0.18 * uncertainty
            ranked.append((acquisition, predicted_score, uncertainty, candidate))

        ranked.sort(key=lambda item: item[0])
        _, predicted_score, uncertainty, params = ranked[0]
        baseline_score = best_observation["score"]
        improvement = max(0.0, (baseline_score - predicted_score) / max(abs(baseline_score), 1e-9))

        return {
            "recommended_parameters": params,
            "expected_improvement": {
                "objective_score": f"-{improvement * 100:.1f}%",
                "uncertainty": round(uncertainty, 4),
            },
            "optimizer": self.name,
            "reasons": [
                f"基于 {len(observations)} 个历史 run 建立 RBF 小样本代理模型。",
                f"当前最佳基准为：{best_observation['label']}。",
                "推荐点综合考虑了预测目标值和未探索区域的不确定性。",
            ],
        }

    def _candidate_params(self, parameter_space: dict, best_params: dict) -> list[dict[str, float]]:
        names = list(parameter_space)
        levels = []
        for name in names:
            bounds = parameter_space[name]
            low = float(bounds["min"])
            high = float(bounds["max"])
            span = high - low
            best = float(best_params.get(name, (low + high) / 2))
            values = {
                low,
                high,
                (low + high) / 2,
                self._clamp(best - span * 0.12, bounds),
                self._clamp(best + span * 0.12, bounds),
            }
            levels.append(sorted(round(value, 4) for value in values))
        return [dict(zip(names, values)) for values in product(*levels)]

    def _predict(self, candidate: dict[str, float], observations: list[dict]) -> tuple[float, float]:
        weighted = 0.0
        total_weight = 0.0
        nearest_distance = float("inf")
        for observation in observations:
            distance = self._distance(candidate, observation["params"])
            nearest_distance = min(nearest_distance, distance)
            weight = exp(-(distance ** 2) / 0.18)
            weighted += observation["score"] * weight
            total_weight += weight
        if total_weight <= 1e-12:
            predicted = sum(item["score"] for item in observations) / len(observations)
        else:
            predicted = weighted / total_weight
        uncertainty = min(1.0, nearest_distance)
        return predicted, uncertainty

    def _normalize(self, params: dict, parameter_space: dict) -> dict[str, float]:
        normalized = {}
        for name, bounds in parameter_space.items():
            low = float(bounds["min"])
            high = float(bounds["max"])
            span = max(high - low, 1e-9)
            normalized[name] = (float(params.get(name, low)) - low) / span
        return normalized

    def _has_declared_params(self, run: dict, parameter_space: dict) -> bool:
        params = run.get("parameters", {})
        return all(name in params for name in parameter_space)

    def _score(self, metrics: dict, config: dict) -> float:
        return HeuristicOptimizerPlugin()._score(metrics, config)

    def _distance(self, left: dict[str, float], right: dict[str, float]) -> float:
        keys = list(left)
        return sqrt(sum((left[key] - right[key]) ** 2 for key in keys) / max(len(keys), 1))

    def _clamp(self, value: float, bounds: dict) -> float:
        return min(max(value, float(bounds["min"])), float(bounds["max"]))
