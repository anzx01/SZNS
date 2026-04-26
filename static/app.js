const state = {
  bundles: [],
  selectedProjectId: null,
  selectedRunId: null,
};

const el = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

async function refresh() {
  const payload = await api("/api/state");
  state.bundles = payload.projects;
  if (!state.selectedProjectId && state.bundles[0]) {
    state.selectedProjectId = state.bundles[0].project.id;
  }
  const project = currentProject();
  if (project && project.runs.length && !state.selectedRunId) {
    state.selectedRunId = project.runs[project.runs.length - 1].id;
  }
  render();
}

function currentProject() {
  return state.bundles.find((bundle) => bundle.project.id === state.selectedProjectId) || state.bundles[0];
}

function currentRun() {
  const project = currentProject();
  if (!project || !project.runs.length) return null;
  return project.runs.find((run) => run.id === state.selectedRunId) || project.runs[project.runs.length - 1];
}

function render() {
  renderProjects();
  renderHeader();
  renderMetrics();
  renderRunPicker();
  renderRuns();
  renderRecommendation();
  drawChart(currentRun());
}

function renderProjects() {
  const list = el("projectList");
  list.innerHTML = "";
  if (!state.bundles.length) {
    list.innerHTML = `<p class="message">还没有项目，先载入演示数据。</p>`;
    return;
  }
  for (const bundle of state.bundles) {
    const button = document.createElement("button");
    button.className = `project-item ${bundle.project.id === state.selectedProjectId ? "active" : ""}`;
    button.innerHTML = `<strong>${escapeHtml(bundle.project.name)}</strong><small>${bundle.runs.length} runs</small>`;
    button.addEventListener("click", () => {
      state.selectedProjectId = bundle.project.id;
      state.selectedRunId = bundle.runs.at(-1)?.id || null;
      render();
    });
    list.appendChild(button);
  }
}

function renderHeader() {
  const project = currentProject();
  el("projectTitle").textContent = project ? project.project.name : "实验项目";
}

function renderMetrics() {
  const run = currentRun();
  const metrics = run?.metrics || {};
  const cells = [
    ["Vds Max", format(metrics.max_vds, " V")],
    ["Ids Max", format(metrics.max_ids, " A")],
    ["过冲比例", metrics.overshoot_ratio === undefined ? "-" : `${(metrics.overshoot_ratio * 100).toFixed(2)}%`],
    ["振荡频率", metrics.ringing_frequency ? `${(metrics.ringing_frequency / 1_000_000).toFixed(2)} MHz` : "-"],
    ["风险等级", metrics.risk_level || "-"],
  ];
  el("metricStrip").innerHTML = cells
    .map(([label, value]) => `<div class="metric-cell"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderRunPicker() {
  const project = currentProject();
  const picker = el("runPicker");
  picker.innerHTML = "";
  if (!project) return;
  for (const run of project.runs) {
    const option = document.createElement("option");
    option.value = run.id;
    option.textContent = run.label || run.id;
    option.selected = run.id === currentRun()?.id;
    picker.appendChild(option);
  }
}

function renderRuns() {
  const project = currentProject();
  const body = el("runRows");
  if (!project || !project.runs.length) {
    body.innerHTML = `<tr><td colspan="7">暂无 run。</td></tr>`;
    return;
  }
  body.innerHTML = project.runs
    .map((run) => {
      const m = run.metrics || {};
      return `<tr>
        <td>${escapeHtml(run.label || run.id)}</td>
        <td>${format(m.max_vds, " V")}</td>
        <td>${format(m.max_ids, " A")}</td>
        <td>${m.overshoot_ratio === undefined ? "-" : `${(m.overshoot_ratio * 100).toFixed(2)}%`}</td>
        <td>${m.ringing_frequency ? `${(m.ringing_frequency / 1_000_000).toFixed(2)} MHz` : "-"}</td>
        <td>${format(m.settling_time_us, " us")}</td>
        <td><span class="risk ${m.risk_level || "low"}">${m.risk_level || "-"}</span></td>
      </tr>`;
    })
    .join("");
}

function renderRecommendation() {
  const project = currentProject();
  const box = el("recommendationBox");
  const rec = project?.recommendations.at(-1);
  if (!rec) {
    box.innerHTML = `<p class="message">暂无推荐。</p>`;
    return;
  }
  const params = Object.entries(rec.recommended_parameters || {})
    .map(([key, value]) => `<div class="param-pill"><span>${escapeHtml(key)}</span><strong>${value}</strong></div>`)
    .join("");
  const safety = rec.safety_result || {};
  const safetyClass = safety.passed ? "safety-pass" : "safety-fail";
  const safetyTitle = safety.passed ? "安全检查通过" : "安全检查拒绝";
  const reasons = rec.reasons || [];
  const warnings = safety.warnings || [];
  const rejects = safety.reasons || [];
  box.innerHTML = `
    <div class="param-list">${params}</div>
    <div class="${safetyClass}"><strong>${safetyTitle}</strong></div>
    <ul class="reason-list">
      ${reasons.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      ${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      ${rejects.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function drawChart(run) {
  const canvas = el("waveCanvas");
  const ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const width = rect.width;
  const height = rect.height;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcf7";
  ctx.fillRect(0, 0, width, height);

  const pad = { left: 52, right: 18, top: 22, bottom: 34 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  drawGrid(ctx, pad, plotW, plotH);

  if (!run || !run.chart?.length) {
    ctx.fillStyle = "#647066";
    ctx.fillText("暂无波形数据", pad.left, pad.top + 24);
    return;
  }

  const points = run.chart;
  const minT = Math.min(...points.map((p) => p.time));
  const maxT = Math.max(...points.map((p) => p.time));
  const maxVds = Math.max(...points.map((p) => p.vds), 1);
  const maxIds = Math.max(...points.map((p) => p.ids), 1);
  const scaleX = (value) => pad.left + ((value - minT) / Math.max(maxT - minT, 1e-12)) * plotW;
  const scaleYV = (value) => pad.top + plotH - (value / maxVds) * plotH;
  const scaleYI = (value) => pad.top + plotH - (value / maxIds) * plotH;

  drawLine(ctx, points, scaleX, scaleYV, "vds", "#b66a3c", 2.4);
  drawLine(ctx, points, scaleX, scaleYI, "ids", "#394d3f", 2);

  ctx.fillStyle = "#17201b";
  ctx.font = "12px Microsoft YaHei, sans-serif";
  ctx.fillText("Vds", pad.left + 8, pad.top + 16);
  ctx.fillStyle = "#394d3f";
  ctx.fillText("Ids", pad.left + 48, pad.top + 16);
}

function drawGrid(ctx, pad, width, height) {
  ctx.strokeStyle = "#d7ded1";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i += 1) {
    const y = pad.top + (height / 5) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + width, y);
    ctx.stroke();
  }
  ctx.strokeStyle = "#9ba796";
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + height);
  ctx.lineTo(pad.left + width, pad.top + height);
  ctx.stroke();
}

function drawLine(ctx, points, scaleX, scaleY, key, color, lineWidth) {
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = scaleX(point.time);
    const y = scaleY(point[key]);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

async function loadDemo() {
  setMessage("正在载入演示数据...");
  await api("/api/demo/load", { method: "POST", body: "{}" });
  state.selectedProjectId = null;
  state.selectedRunId = null;
  await refresh();
  setMessage("演示闭环已生成。");
}

async function createRecommendation() {
  const project = currentProject();
  if (!project) return setMessage("请先载入或创建项目。");
  setMessage("正在生成参数推荐...");
  await api("/api/recommendations", {
    method: "POST",
    body: JSON.stringify({ project_id: project.project.id }),
  });
  await refresh();
  setMessage("推荐已生成。");
}

async function generateReport() {
  const project = currentProject();
  if (!project) return setMessage("请先载入或创建项目。");
  setMessage("正在生成报告...");
  const report = await api("/api/reports", {
    method: "POST",
    body: JSON.stringify({ project_id: project.project.id }),
  });
  await refresh();
  window.open(report.url, "_blank");
  setMessage("报告已生成。");
}

async function importRun() {
  const project = currentProject();
  const file = el("dataFile").files[0];
  if (!project) return setMessage("请先载入演示项目。");
  if (!file) return setMessage("请选择 CSV 或 JSON 文件。");
  setMessage("正在导入并计算指标...");
  const content = await file.text();
  const dataset = await api("/api/datasets/import", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      filename: file.name,
      content,
    }),
  });
  const run = await api("/api/runs", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      dataset_id: dataset.id,
      label: el("runLabel").value || file.name,
      parameters: {
        dead_time: Number(el("deadTime").value),
        gate_resistance: Number(el("gateResistance").value),
        drive_voltage: Number(el("driveVoltage").value),
        damping_resistance: Number(el("dampingResistance").value),
      },
    }),
  });
  state.selectedRunId = run.id;
  await refresh();
  setMessage("run 已记录。");
}

function setMessage(text) {
  el("message").textContent = text;
}

function format(value, unit = "") {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return `${Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 4 })}${unit}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

el("loadDemo").addEventListener("click", () => loadDemo().catch((error) => setMessage(error.message)));
el("recommendBtn").addEventListener("click", () => createRecommendation().catch((error) => setMessage(error.message)));
el("reportBtn").addEventListener("click", () => generateReport().catch((error) => setMessage(error.message)));
el("importRunBtn").addEventListener("click", () => importRun().catch((error) => setMessage(error.message)));
el("runPicker").addEventListener("change", (event) => {
  state.selectedRunId = event.target.value;
  render();
});
window.addEventListener("resize", () => drawChart(currentRun()));

refresh().catch((error) => setMessage(error.message));

