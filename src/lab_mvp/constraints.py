from __future__ import annotations


class SiCGaNConstraintPlugin:
    name = "SiCGaNConstraintPlugin"

    def check(self, recommendation: dict, config: dict) -> dict:
        params = recommendation.get("recommended_parameters", {})
        parameter_space = config.get("parameter_space", {})
        passed = True
        reasons: list[str] = []
        warnings: list[str] = []

        for name, value in params.items():
            bounds = parameter_space.get(name)
            if not bounds:
                passed = False
                reasons.append(f"{name} 未在参数空间中声明。")
                continue
            if value < bounds["min"] or value > bounds["max"]:
                passed = False
                reasons.append(f"{name}={value} 超出允许范围 [{bounds['min']}, {bounds['max']}].")

        drive_voltage = params.get("drive_voltage")
        gate_resistance = params.get("gate_resistance")
        dead_time = params.get("dead_time")

        if drive_voltage is not None and gate_resistance is not None:
            if drive_voltage > 17 and gate_resistance < 2.5:
                passed = False
                reasons.append("高驱动电压与低栅极电阻组合风险过高。")
            elif drive_voltage > 17 and gate_resistance < 4:
                warnings.append("驱动电压较高且栅极电阻偏低，建议先仿真验证。")

        if dead_time is not None and dead_time < 80:
            warnings.append("死区时间低于 80ns，真实设备执行前必须人工复核。")

        return {
            "passed": passed,
            "reasons": reasons,
            "warnings": warnings,
        }

