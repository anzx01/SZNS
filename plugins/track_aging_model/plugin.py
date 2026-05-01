from __future__ import annotations

import math


class TrackAgingModelPlugin:
    """轨道绝缘加速老化数字孪生，作为外部 model 插件样例。

    模拟在持续湿热环境下，绝缘电阻随时间的衰退过程。
    fast 模式输出 12 个点（小时级），high_fidelity 输出 48 个点（15 分钟级）。
    """

    name = "TrackAgingModelPlugin"

    def simulate(self, parameters: dict, config: dict, mode: str = "fast") -> list[dict]:
        test_voltage = float(parameters.get("test_voltage", 500.0))
        alarm_threshold = float(parameters.get("alarm_threshold", 2.0))
        detection_period = float(parameters.get("detection_period", 6.0))
        calibration = config.get("model_calibration", {})

        point_count = 48 if mode == "high_fidelity" else 12
        total_hours = detection_period * 2

        # 初始绝缘电阻（根据测试电压和标称阈值估算）
        initial_resistance = max(1.0, alarm_threshold * 2.8 - (test_voltage - 450) / 600)
        initial_resistance *= float(calibration.get("resistance_scale", 1.0))

        # 老化速率受湿度基线影响
        humidity_base = min(95.0, 65.0 + detection_period * 1.5)
        aging_rate = 0.012 + max(0.0, humidity_base - 70) * 0.0008

        rows: list[dict] = []
        for i in range(point_count):
            hour = i * (total_hours / max(point_count - 1, 1))
            humidity = humidity_base + math.sin(hour / 3.0) * 5.0 + math.sin(hour / 0.8) * 1.5
            temperature = 28.0 + hour * 0.35 + math.sin(hour / 6.0) * 2.0
            humidity_penalty = max(0.0, humidity - 72) * 0.022
            aging_factor = math.exp(-(aging_rate + humidity_penalty * 0.001) * hour)
            resistance = max(0.15, initial_resistance * aging_factor)
            current_ma = test_voltage / (resistance * 1_000_000) * 1000
            rows.append({
                "time": round(hour, 5),
                "voltage": round(test_voltage, 4),
                "current": round(current_ma, 6),
                "humidity": round(humidity, 4),
                "temperature": round(temperature, 4),
            })
        return rows
