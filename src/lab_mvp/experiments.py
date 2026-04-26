from __future__ import annotations

import csv
from io import StringIO


EXPERIMENTS = {
    "sic_gan_switching": {
        "type": "sic_gan_switching",
        "name": "SiC/GaN 关断振荡优化",
        "description": "用于电力电子器件关断振荡、过冲和损耗折中的实验优化。",
        "required_signals": ("time", "vgs", "vds", "ids"),
        "optional_signals": ("temperature",),
        "field_aliases": {
            "time": ("t", "timestamp", "sample_time"),
            "vgs": ("vg", "gate_voltage", "gate-source voltage", "v_gate"),
            "vds": ("v_ds", "vds_voltage", "drain_source_voltage", "drain-source voltage"),
            "ids": ("id", "i_d", "idrain", "drain_current", "drain current"),
            "temperature": ("temp", "case_temperature", "junction_temperature"),
        },
        "chart_series": ("vds", "ids"),
        "template_row": {
            "time": "0.0000000",
            "vgs": "15.0",
            "vds": "720.0",
            "ids": "40.0",
            "temperature": "32.0",
        },
        "parameters": ("dead_time", "gate_resistance", "drive_voltage", "damping_resistance"),
        "metrics": (
            "max_vds",
            "max_ids",
            "overshoot_ratio",
            "ringing_frequency",
            "settling_time_us",
            "switching_loss_estimate",
            "risk_level",
        ),
        "plugins": {
            "model": "SiCGaNDigitalTwinPlugin",
            "feature": "SiCGaNFeaturePlugin",
            "constraint": "SiCGaNConstraintPlugin",
            "report": "HTMLReportPlugin",
        },
        "safety_contract": (
            "参数空间边界检查",
            "Vds/Ids/温度阈值检查",
            "高驱动电压 + 低栅极电阻危险组合检查",
        ),
    },
    "track_insulation": {
        "type": "track_insulation",
        "name": "轨道绝缘检测",
        "description": "用于轨道绝缘电阻、泄漏电流和环境压力的检测策略优化。",
        "required_signals": ("time", "voltage", "current"),
        "optional_signals": ("humidity", "temperature"),
        "field_aliases": {
            "time": ("t", "timestamp", "sample_time"),
            "voltage": ("test_voltage", "u", "u_test", "v_test"),
            "current": ("leakage", "leakage_current", "leakage_ma", "i_leak", "current_ma"),
            "humidity": ("rh", "relative_humidity"),
            "temperature": ("temp", "ambient_temperature"),
        },
        "chart_series": ("voltage", "current"),
        "template_row": {
            "time": "0",
            "voltage": "500",
            "current": "0.20",
            "humidity": "80",
            "temperature": "32",
        },
        "parameters": ("test_voltage", "detection_period", "alarm_threshold"),
        "metrics": (
            "min_insulation_mohm",
            "avg_insulation_mohm",
            "max_leakage_ma",
            "degradation_index",
            "environment_stress",
            "risk_level",
        ),
        "plugins": {
            "model": "TrackInsulationDigitalTwinPlugin",
            "feature": "TrackInsulationFeaturePlugin",
            "constraint": "TrackInsulationConstraintPlugin",
            "report": "HTMLReportPlugin",
        },
        "safety_contract": (
            "参数空间边界检查",
            "测试电压上限检查",
            "最低绝缘电阻与最大泄漏电流风险检查",
            "湿度环境上限检查",
        ),
    },
}


def experiment_manifest(experiment_type: str) -> dict:
    if experiment_type not in EXPERIMENTS:
        raise ValueError(f"未知实验类型：{experiment_type}")
    return EXPERIMENTS[experiment_type]


def all_experiment_manifests() -> list[dict]:
    return list(EXPERIMENTS.values())


def csv_template(experiment_type: str) -> str:
    manifest = experiment_manifest(experiment_type)
    headers = [*manifest["required_signals"], *manifest.get("optional_signals", ())]
    row = manifest.get("template_row", {})
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerow({name: row.get(name, "") for name in headers})
    return buffer.getvalue()
