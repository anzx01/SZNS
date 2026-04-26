from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_sic_gan_config(project_id: str) -> dict:
    return {
        "id": new_id("config"),
        "project_id": project_id,
        "name": "SiC/GaN default safety envelope",
        "parameter_space": {
            "dead_time": {"min": 50, "max": 500, "unit": "ns"},
            "gate_resistance": {"min": 1, "max": 20, "unit": "ohm"},
            "drive_voltage": {"min": 12, "max": 18, "unit": "V"},
            "damping_resistance": {"min": 0, "max": 10, "unit": "ohm"},
        },
        "safety_limits": {
            "max_vds": 900,
            "max_ids": 50,
            "max_temperature": 100,
        },
        "objective_weights": {
            "overshoot_ratio": 0.4,
            "settling_time_us": 0.3,
            "switching_loss_estimate": 0.3,
        },
        "model_calibration": {},
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }


def default_track_insulation_config(project_id: str) -> dict:
    return {
        "id": new_id("config"),
        "project_id": project_id,
        "name": "Track insulation default safety envelope",
        "parameter_space": {
            "test_voltage": {"min": 250, "max": 1000, "unit": "V"},
            "detection_period": {"min": 1, "max": 24, "unit": "h"},
            "alarm_threshold": {"min": 0.5, "max": 10, "unit": "MOhm"},
        },
        "safety_limits": {
            "max_test_voltage": 1000,
            "min_insulation_mohm": 1.0,
            "max_leakage_ma": 2.0,
            "max_humidity": 95,
        },
        "objective_weights": {
            "degradation_index": 0.45,
            "max_leakage_ma": 0.35,
            "environment_stress": 0.2,
        },
        "model_calibration": {},
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }


def default_config_for(experiment_type: str, project_id: str) -> dict:
    if experiment_type == "track_insulation":
        return default_track_insulation_config(project_id)
    return default_sic_gan_config(project_id)
