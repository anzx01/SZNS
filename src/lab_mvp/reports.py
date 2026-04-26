from __future__ import annotations

from html import escape


class HTMLReportPlugin:
    name = "HTMLReportPlugin"

    def generate(self, project: dict, runs: list[dict], recommendations: list[dict]) -> str:
        rows = "\n".join(self._run_row(run) for run in runs)
        recs = "\n".join(self._recommendation_card(rec) for rec in recommendations[-3:])
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
    <h2>Run 对比</h2>
    <table>
      <thead>
        <tr>
          <th>Run</th><th>Vds Max</th><th>Ids Max</th><th>过冲</th><th>振荡频率</th><th>衰减时间</th><th>风险</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <h2>最近推荐</h2>
    {recs or '<p class="muted">暂无推荐记录。</p>'}
  </main>
</body>
</html>"""

    def _run_row(self, run: dict) -> str:
        metrics = run.get("metrics", {})
        return "<tr>" + "".join(
            f"<td>{escape(str(value))}</td>"
            for value in [
                run.get("label") or run["id"],
                metrics.get("max_vds", "-"),
                metrics.get("max_ids", "-"),
                metrics.get("overshoot_ratio", "-"),
                metrics.get("ringing_frequency", "-"),
                metrics.get("settling_time_us", "-"),
                metrics.get("risk_level", "-"),
            ]
        ) + "</tr>"

    def _recommendation_card(self, recommendation: dict) -> str:
        params = ", ".join(
            f"{escape(key)}={escape(str(value))}"
            for key, value in recommendation.get("recommended_parameters", {}).items()
        )
        safety = recommendation.get("safety_result", {})
        status = "通过" if safety.get("passed") else "拒绝"
        reasons = "; ".join(recommendation.get("reasons", []))
        return f"""
<section class="card">
  <strong>{escape(status)}</strong>
  <p>推荐参数：{params}</p>
  <p class="muted">{escape(reasons)}</p>
</section>"""

