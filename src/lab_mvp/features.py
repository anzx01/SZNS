from __future__ import annotations

from statistics import median


class SiCGaNFeaturePlugin:
    name = "SiCGaNFeaturePlugin"

    def extract(self, rows: list[dict[str, float]], config: dict) -> dict:
        time = [row["time"] for row in rows]
        vds = [row["vds"] for row in rows]
        ids = [row["ids"] for row in rows]
        temperatures = [row.get("temperature") for row in rows if row.get("temperature") is not None]

        steady_vds = self._steady_value(vds)
        max_vds = max(vds)
        max_ids = max(ids)
        min_ids = min(ids)
        overshoot_ratio = max(0.0, (max_vds - steady_vds) / max(abs(steady_vds), 1e-9))
        ringing_frequency = self._ringing_frequency(time, vds)
        settling_time_us = self._settling_time_us(time, vds, steady_vds)
        switching_loss = self._switching_loss(time, vds, ids)
        max_temperature = max(temperatures) if temperatures else None
        risk_level, risk_flags = self._risk(max_vds, max_ids, max_temperature, config)

        return {
            "max_vds": round(max_vds, 4),
            "steady_vds": round(steady_vds, 4),
            "max_ids": round(max_ids, 4),
            "min_ids": round(min_ids, 4),
            "overshoot_ratio": round(overshoot_ratio, 5),
            "ringing_frequency": round(ringing_frequency, 2),
            "settling_time_us": round(settling_time_us, 4),
            "switching_loss_estimate": round(switching_loss, 6),
            "max_temperature": round(max_temperature, 3) if max_temperature is not None else None,
            "risk_level": risk_level,
            "risk_flags": risk_flags,
        }

    def _steady_value(self, values: list[float]) -> float:
        tail_count = max(5, len(values) // 10)
        return median(values[-tail_count:])

    def _ringing_frequency(self, time: list[float], values: list[float]) -> float:
        if len(values) < 5:
            return 0.0
        threshold = self._steady_value(values) + (max(values) - self._steady_value(values)) * 0.08
        peaks: list[int] = []
        for index in range(1, len(values) - 1):
            if values[index] > threshold and values[index] > values[index - 1] and values[index] >= values[index + 1]:
                peaks.append(index)
        if len(peaks) < 2:
            return 0.0
        periods = [time[b] - time[a] for a, b in zip(peaks, peaks[1:]) if time[b] > time[a]]
        if not periods:
            return 0.0
        avg_period = sum(periods) / len(periods)
        return 1.0 / avg_period if avg_period > 0 else 0.0

    def _settling_time_us(self, time: list[float], values: list[float], steady: float) -> float:
        peak_index = max(range(len(values)), key=lambda index: values[index])
        tolerance = max(abs(steady) * 0.05, 1.0)
        required = 4
        stable_count = 0
        for index in range(peak_index, len(values)):
            if abs(values[index] - steady) <= tolerance:
                stable_count += 1
            else:
                stable_count = 0
            if stable_count >= required:
                settled_index = index - required + 1
                return max(0.0, (time[settled_index] - time[peak_index]) * 1_000_000)
        return max(0.0, (time[-1] - time[peak_index]) * 1_000_000)

    def _switching_loss(self, time: list[float], vds: list[float], ids: list[float]) -> float:
        total = 0.0
        for index in range(1, len(time)):
            dt = max(0.0, time[index] - time[index - 1])
            p0 = abs(vds[index - 1] * ids[index - 1])
            p1 = abs(vds[index] * ids[index])
            total += (p0 + p1) * 0.5 * dt
        return total

    def _risk(self, max_vds: float, max_ids: float, max_temperature: float | None, config: dict) -> tuple[str, list[str]]:
        limits = config.get("safety_limits", {})
        flags: list[str] = []
        if max_vds >= limits.get("max_vds", float("inf")):
            flags.append("Vds 超出安全上限")
        elif max_vds >= limits.get("max_vds", float("inf")) * 0.92:
            flags.append("Vds 接近安全上限")
        if max_ids >= limits.get("max_ids", float("inf")):
            flags.append("Ids 超出安全上限")
        elif max_ids >= limits.get("max_ids", float("inf")) * 0.92:
            flags.append("Ids 接近安全上限")
        if max_temperature is not None and max_temperature >= limits.get("max_temperature", float("inf")):
            flags.append("温度超出安全上限")

        if any("超出" in item for item in flags):
            return "high", flags
        if flags:
            return "medium", flags
        return "low", []


class TrackInsulationFeaturePlugin:
    name = "TrackInsulationFeaturePlugin"

    def extract(self, rows: list[dict[str, float]], config: dict) -> dict:
        resistances = [self._resistance_mohm(row["voltage"], row["current"]) for row in rows]
        leakages = [abs(row["current"]) for row in rows]
        humidity_values = [row.get("humidity") for row in rows if row.get("humidity") is not None]
        temperature_values = [row.get("temperature") for row in rows if row.get("temperature") is not None]

        min_resistance = min(resistances)
        avg_resistance = sum(resistances) / len(resistances)
        max_leakage = max(leakages)
        max_humidity = max(humidity_values) if humidity_values else None
        max_temperature = max(temperature_values) if temperature_values else None
        alarm_threshold = config.get("safety_limits", {}).get("min_insulation_mohm", 1.0)
        degradation_index = max(0.0, (alarm_threshold - min_resistance) / max(alarm_threshold, 1e-9))
        environment_stress = self._environment_stress(max_humidity, max_temperature)
        risk_level, risk_flags = self._risk(
            min_resistance,
            max_leakage,
            max_humidity,
            config,
        )

        return {
            "min_insulation_mohm": round(min_resistance, 4),
            "avg_insulation_mohm": round(avg_resistance, 4),
            "max_leakage_ma": round(max_leakage, 5),
            "max_humidity": round(max_humidity, 3) if max_humidity is not None else None,
            "max_temperature": round(max_temperature, 3) if max_temperature is not None else None,
            "degradation_index": round(degradation_index, 5),
            "environment_stress": round(environment_stress, 5),
            "risk_level": risk_level,
            "risk_flags": risk_flags,
        }

    def _resistance_mohm(self, voltage: float, current_ma: float) -> float:
        current_amp = max(abs(current_ma) / 1000, 1e-9)
        return abs(voltage) / current_amp / 1_000_000

    def _environment_stress(self, humidity: float | None, temperature: float | None) -> float:
        humidity_score = 0.0 if humidity is None else max(0.0, (humidity - 70) / 30)
        temperature_score = 0.0 if temperature is None else max(0.0, (temperature - 35) / 35)
        return min(1.0, humidity_score * 0.7 + temperature_score * 0.3)

    def _risk(
        self,
        min_resistance: float,
        max_leakage: float,
        max_humidity: float | None,
        config: dict,
    ) -> tuple[str, list[str]]:
        limits = config.get("safety_limits", {})
        flags: list[str] = []
        if min_resistance < limits.get("min_insulation_mohm", 1.0):
            flags.append("绝缘电阻低于安全阈值")
        elif min_resistance < limits.get("min_insulation_mohm", 1.0) * 1.25:
            flags.append("绝缘电阻接近安全阈值")

        if max_leakage > limits.get("max_leakage_ma", float("inf")):
            flags.append("泄漏电流超出安全上限")
        elif max_leakage > limits.get("max_leakage_ma", float("inf")) * 0.85:
            flags.append("泄漏电流接近安全上限")

        if max_humidity is not None and max_humidity > limits.get("max_humidity", 100):
            flags.append("湿度超出环境上限")

        if any("低于" in item or "超出" in item for item in flags):
            return "high", flags
        if flags:
            return "medium", flags
        return "low", []
