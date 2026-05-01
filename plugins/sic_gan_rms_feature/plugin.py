from __future__ import annotations

import math


class SiCGaNRmsFeaturePlugin:
    """补充 RMS 功率分析特征，作为内置特征提取插件的扩展样例。"""

    name = "SiCGaNRmsFeaturePlugin"

    def extract(self, rows: list[dict], config: dict) -> dict:
        if not rows:
            return {}

        vds_vals = [float(row.get("vds") or 0) for row in rows]
        ids_vals = [float(row.get("ids") or 0) for row in rows]
        time_vals = [float(row.get("time") or 0) for row in rows]

        vds_rms = self._rms(vds_vals)
        ids_rms = self._rms(ids_vals)
        power_inst = [abs(v * i) for v, i in zip(vds_vals, ids_vals)]
        peak_power = max(power_inst)
        energy_j = self._trapz_energy(time_vals, power_inst)

        thermal_resistance = config.get("thermal_resistance_k_per_w", 0.5)
        estimated_temp_rise = energy_j * thermal_resistance * 1000

        return {
            "vds_rms": round(vds_rms, 4),
            "ids_rms": round(ids_rms, 4),
            "peak_instantaneous_power_w": round(peak_power, 4),
            "energy_loss_j": round(energy_j, 8),
            "estimated_temp_rise_k": round(estimated_temp_rise, 4),
            "rms_plugin": self.name,
        }

    def _rms(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return math.sqrt(sum(v * v for v in values) / len(values))

    def _trapz_energy(self, time: list[float], power: list[float]) -> float:
        total = 0.0
        for i in range(1, len(time)):
            dt = max(0.0, time[i] - time[i - 1])
            total += (power[i - 1] + power[i]) * 0.5 * dt
        return total
