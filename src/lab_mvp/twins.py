from __future__ import annotations

import math


class SiCGaNDigitalTwinPlugin:
    name = "SiCGaNDigitalTwinPlugin"

    def simulate(self, parameters: dict, config: dict, mode: str = "fast") -> list[dict[str, float]]:
        dead_time = parameters.get("dead_time", 140.0)
        gate_resistance = parameters.get("gate_resistance", 5.0)
        drive_voltage = parameters.get("drive_voltage", 15.0)
        damping = parameters.get("damping_resistance", 2.0)
        calibration = config.get("model_calibration", {})
        point_count = 81 if mode == "high_fidelity" else 41
        dt = 5e-8 if mode == "high_fidelity" else 1e-7

        steady_vds = 720.0
        overshoot = max(0.04, 0.24 + (drive_voltage - 15.0) * 0.025 - gate_resistance * 0.012 - damping * 0.01)
        overshoot *= calibration.get("overshoot_scale", 1.0)
        ring_decay = max(0.18, 0.95 - gate_resistance * 0.045 - damping * 0.08 + max(0.0, 120 - dead_time) * 0.002)
        frequency_hz = 5_000_000 + (drive_voltage - 15.0) * 350_000 - damping * 120_000
        peak_ids = max(12.0, 42.0 + (drive_voltage - 15.0) * 2.4 - gate_resistance * 0.6) * calibration.get("ids_scale", 1.0)
        temperature_base = 31.0 + drive_voltage * 0.18 + max(0.0, 180 - dead_time) * 0.01

        rows: list[dict[str, float]] = []
        transition_points = 7 if mode == "high_fidelity" else 4
        for index in range(point_count):
            time = index * dt
            if index < transition_points:
                progress = index / max(transition_points - 1, 1)
                vds = 50 + steady_vds * progress
                ids = peak_ids * (1 - progress * 0.3)
                vgs = drive_voltage * (1 - progress * 0.65)
            else:
                elapsed = (index - transition_points) * dt
                envelope = math.exp(-elapsed / (ring_decay * 1e-6))
                oscillation = math.cos(2 * math.pi * frequency_hz * elapsed)
                vds = steady_vds + steady_vds * overshoot * envelope * oscillation
                ids = max(0.2, peak_ids * math.exp(-(index - 4) / 7.5))
                vgs = max(0.0, drive_voltage * math.exp(-(index - 4) / 2.0) * 0.15)
            rows.append(
                {
                    "time": round(time, 10),
                    "vgs": round(vgs, 5),
                    "vds": round(vds, 5),
                    "ids": round(ids, 5),
                    "temperature": round(temperature_base + index * 0.08, 4),
                }
            )
        return rows


class TrackInsulationDigitalTwinPlugin:
    name = "TrackInsulationDigitalTwinPlugin"

    def simulate(self, parameters: dict, config: dict, mode: str = "fast") -> list[dict[str, float]]:
        test_voltage = parameters.get("test_voltage", 500.0)
        detection_period = parameters.get("detection_period", 6.0)
        alarm_threshold = parameters.get("alarm_threshold", 2.0)
        calibration = config.get("model_calibration", {})
        point_count = 24 if mode == "high_fidelity" else 12

        base_resistance_mohm = max(0.35, alarm_threshold * 1.75 - (test_voltage - 450) / 400)
        base_resistance_mohm *= calibration.get("resistance_scale", 1.0)
        humidity_base = min(94.0, 68.0 + detection_period * 1.2)
        rows: list[dict[str, float]] = []
        for index in range(point_count):
            hour = index * (12 / point_count)
            humidity = humidity_base + math.sin(hour / 2.0) * 4.0
            temperature = 29.0 + hour * 0.45
            humidity_penalty = max(0.0, humidity - 75.0) * 0.018
            resistance = max(0.25, base_resistance_mohm - humidity_penalty - hour * 0.025)
            current_ma = test_voltage / (resistance * 1_000_000) * 1000
            rows.append(
                {
                    "time": round(hour, 5),
                    "voltage": round(test_voltage, 4),
                    "current": round(current_ma, 6),
                    "humidity": round(humidity, 4),
                    "temperature": round(temperature, 4),
                }
            )
        return rows
