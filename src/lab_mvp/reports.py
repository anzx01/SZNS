from __future__ import annotations

from html import escape


class HTMLReportPlugin:
    name = "HTMLReportPlugin"

    def generate(
        self,
        project: dict,
        runs: list[dict],
        recommendations: list[dict],
        config: dict | None = None,
        manifest: dict | None = None,
        events: list[dict] | None = None,
    ) -> str:
        columns = self._columns(project.get("experiment_type", "sic_gan_switching"))
        rows = "\n".join(self._run_row(run, columns) for run in runs)
        header = "".join(f"<th>{escape(label)}</th>" for _, label in columns)
        recs = "\n".join(self._recommendation_card(rec) for rec in recommendations[-3:])
        event_rows = "\n".join(self._event_row(event) for event in (events or [])[-8:])
        calibration = config.get("model_calibration", {}) if config else {}
        plugins = ", ".join((manifest or {}).get("plugins", {}).values())
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{escape(project["name"])} 实验报告</title>
  <style>
    body {{ margin: 0; font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; color: #16211c; background: #f6f7f2; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 40px; }}
    h1 {{ font-size: 30px; margin: 0 0 8px; }}
    h2 {{ margin-top: 34px; border-bottom: 1px solid #cfd6ca; padding-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #e4e7df; font-size: 14px; }}
    th {{ color: #5a665d; background: #eef1e8; }}
    .card {{ background: #fff; border: 1px solid #dbe0d5; border-radius: 8px; padding: 16px; margin: 12px 0; }}
    .muted {{ color: #68746b; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(project["name"])}</h1>
    <p class="muted">实验类型：{escape(project["experiment_type"])}。本报告由 MVP 平台自动生成。</p>
    <section class="card">
      <strong>插件</strong>
      <p class="muted">{escape(plugins or '-')}</p>
      <strong>模型校准</strong>
      <p class="muted">{escape(str(calibration or '未校准'))}</p>
    </section>
    <h2>Run 对比</h2>
    <table>
      <thead>
        <tr>
          <th>Run</th>{header}<th>风险</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <h2>最近推荐</h2>
    {recs or '<p class="muted">暂无推荐记录。</p>'}
    <h2>实验日志</h2>
    <table>
      <thead><tr><th>时间</th><th>事件</th><th>说明</th></tr></thead>
      <tbody>{event_rows}</tbody>
    </table>
  </main>
</body>
</html>"""

    def _columns(self, experiment_type: str) -> list[tuple[str, str]]:
        if experiment_type == "track_insulation":
            return [
                ("min_insulation_mohm", "最低绝缘 MOhm"),
                ("avg_insulation_mohm", "平均绝缘 MOhm"),
                ("max_leakage_ma", "最大泄漏 mA"),
                ("max_humidity", "最高湿度"),
                ("degradation_index", "退化指数"),
            ]
        return [
            ("max_vds", "Vds Max"),
            ("max_ids", "Ids Max"),
            ("overshoot_ratio", "过冲"),
            ("ringing_frequency", "振荡频率"),
            ("settling_time_us", "衰减时间"),
        ]

    def _run_row(self, run: dict, columns: list[tuple[str, str]]) -> str:
        metrics = run.get("metrics", {})
        label = run.get("label") or run["id"]
        if run.get("source_type") == "simulation":
            label = f"{label} (sim/{run.get('model_mode', 'fast')})"
        values = [label]
        values.extend(metrics.get(key, "-") for key, _ in columns)
        values.append(metrics.get("risk_level", "-"))
        return "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in values) + "</tr>"

    def _event_row(self, event: dict) -> str:
        return "<tr>" + "".join(
            f"<td>{escape(str(value))}</td>"
            for value in [event.get("created_at", "-"), event.get("type", "-"), event.get("message", "-")]
        ) + "</tr>"

    def _recommendation_card(self, recommendation: dict) -> str:
        params = ", ".join(
            f"{escape(key)}={escape(str(value))}"
            for key, value in recommendation.get("recommended_parameters", {}).items()
        )
        safety = recommendation.get("safety_result", {})
        status = "通过" if safety.get("passed") else "拒绝"
        reasons = "; ".join(recommendation.get("reasons", []))
        optimizer = recommendation.get("optimizer", "-")
        return f"""
<section class="card">
  <strong>{escape(status)}</strong>
  <p class="muted">优化器：{escape(optimizer)}</p>
  <p>推荐参数：{params}</p>
  <p class="muted">{escape(reasons)}</p>
</section>"""
