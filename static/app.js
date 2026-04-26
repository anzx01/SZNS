const state = {
  bundles: [],
  experiments: [],
  pluginCatalog: [],
  selectedProjectId: null,
  selectedRunId: null,
  importPreview: null,
};

const el = (id) => document.getElementById(id);

const EXPERIMENT_UI = {
  sic_gan_switching: {
    eyebrow: "SiC/GaN switching lab",
    chart: [
      { key: "vds", label: "Vds", color: "#b66a3c" },
      { key: "ids", label: "Ids", color: "#394d3f" },
    ],
    metrics: [
      ["max_vds", "Vds Max", " V"],
      ["max_ids", "Ids Max", " A"],
      ["overshoot_ratio", "过冲比例", "%"],
      ["ringing_frequency", "振荡频率", "MHz"],
      ["risk_level", "风险等级", ""],
    ],
    table: [
      ["max_vds", "Vds Max", " V"],
      ["max_ids", "Ids Max", " A"],
      ["overshoot_ratio", "过冲", "%"],
      ["ringing_frequency", "频率", "MHz"],
      ["settling_time_us", "衰减", " us"],
    ],
  },
  track_insulation: {
    eyebrow: "Track insulation lab",
    chart: [
      { key: "voltage", label: "Voltage", color: "#b66a3c" },
      { key: "current", label: "Leakage", color: "#394d3f" },
    ],
    metrics: [
      ["min_insulation_mohm", "最低绝缘", " MOhm"],
      ["max_leakage_ma", "最大泄漏", " mA"],
      ["max_humidity", "最高湿度", "%"],
      ["degradation_index", "退化指数", ""],
      ["risk_level", "风险等级", ""],
    ],
    table: [
      ["min_insulation_mohm", "最低绝缘", " MOhm"],
      ["avg_insulation_mohm", "平均绝缘", " MOhm"],
      ["max_leakage_ma", "最大泄漏", " mA"],
      ["max_humidity", "湿度", "%"],
      ["degradation_index", "退化", ""],
    ],
  },
};

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
  state.experiments = payload.experiments || [];
  state.pluginCatalog = payload.plugin_catalog || [];
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
  renderProjectCreator();
  renderProjects();
  renderHeader();
  renderMetrics();
  renderRunPicker();
  renderRunParamInputs();
  renderRuns();
  renderRecommendation();
  renderConfig();
  renderManifest();
  renderEvents();
  renderPluginCatalog();
  renderImportPreview();
  drawChart(currentRun());
}

function renderProjectCreator() {
  const select = el("newProjectType");
  const previous = select.value;
  select.innerHTML = state.experiments
    .map((experiment) => `<option value="${escapeHtml(experiment.type)}">${escapeHtml(experiment.name)}</option>`)
    .join("");
  if (previous && state.experiments.some((experiment) => experiment.type === previous)) {
    select.value = previous;
  }
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
    button.innerHTML = `<strong>${escapeHtml(bundle.project.name)}</strong><small>${escapeHtml(bundle.manifest?.name || bundle.project.experiment_type)} · ${bundle.runs.length} runs</small>`;
    button.addEventListener("click", () => {
      state.selectedProjectId = bundle.project.id;
      state.selectedRunId = bundle.runs.at(-1)?.id || null;
      state.importPreview = null;
      render();
    });
    list.appendChild(button);
  }
}

function renderHeader() {
  const project = currentProject();
  el("projectTitle").textContent = project ? project.project.name : "实验项目";
  document.querySelector(".eyebrow").textContent = uiFor(project).eyebrow;
}

function renderMetrics() {
  const run = currentRun();
  const metrics = run?.metrics || {};
  const cells = uiFor(currentProject()).metrics.map(([key, label, unit]) => [label, formatMetric(key, metrics[key], unit)]);
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
  const headers = document.querySelector("#runRows").closest("table").querySelector("thead tr");
  const tableColumns = uiFor(project).table;
  headers.innerHTML = `<th>Run</th>${tableColumns.map(([, label]) => `<th>${label}</th>`).join("")}<th>风险</th>`;
  if (!project || !project.runs.length) {
    body.innerHTML = `<tr><td colspan="${tableColumns.length + 2}">暂无 run。</td></tr>`;
    return;
  }
  body.innerHTML = project.runs
    .map((run) => {
      const m = run.metrics || {};
      const label = run.source_type === "simulation" ? `${run.label || run.id} · sim` : (run.label || run.id);
      const cells = tableColumns
        .map(([key, , unit]) => `<td>${formatMetric(key, m[key], unit)}</td>`)
        .join("");
      return `<tr>
        <td>${escapeHtml(label)}</td>
        ${cells}
        <td><span class="risk ${m.risk_level || "low"}">${m.risk_level || "-"}</span></td>
      </tr>`;
    })
    .join("");
}

function renderRunParamInputs() {
  const project = currentProject();
  const config = project?.config;
  const container = el("runParamInputs");
  if (!config) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = Object.entries(config.parameter_space || {})
    .map(([name, bounds]) => {
      const value = (Number(bounds.min) + Number(bounds.max)) / 2;
      return `
        <label class="field">
          <span>${labelFor(name)} ${escapeHtml(bounds.unit || "")}</span>
          <input data-run-param="${escapeHtml(name)}" type="number" value="${round(value)}">
        </label>
      `;
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
    <button class="secondary-action full" data-verify-rec="${escapeHtml(rec.id)}">仿真验证推荐</button>
    <ul class="reason-list">
      ${reasons.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      ${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      ${rejects.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function renderPluginCatalog() {
  const container = el("pluginCatalog");
  if (!container) return;
  const project = currentProject();
  const activeType = project?.project?.experiment_type;
  const plugins = state.pluginCatalog.filter((plugin) => !plugin.experiment_type || plugin.experiment_type === activeType);
  if (!plugins.length) {
    container.innerHTML = `<p class="message">暂无插件。</p>`;
    return;
  }
  container.innerHTML = plugins
    .map((plugin) => `
      <article class="plugin-card">
        <strong>${escapeHtml(plugin.name)}</strong>
        <small>${escapeHtml(plugin.type)} · ${escapeHtml(plugin.status || "active")}</small>
      </article>
    `)
    .join("");
}

function renderConfig() {
  const project = currentProject();
  const config = project?.config;
  if (!config) {
    el("parameterConfig").innerHTML = `<p class="message">暂无配置。</p>`;
    el("safetyConfig").innerHTML = "";
    el("weightConfig").innerHTML = "";
    return;
  }
  el("parameterConfig").innerHTML = Object.entries(config.parameter_space || {})
    .map(([name, bounds]) => `
      <div class="config-row" data-param="${escapeHtml(name)}">
        <div class="config-label">${labelFor(name)} <small>${escapeHtml(bounds.unit || "")}</small></div>
        <input class="config-input" data-kind="param-min" data-name="${escapeHtml(name)}" type="number" value="${bounds.min}">
        <input class="config-input" data-kind="param-max" data-name="${escapeHtml(name)}" type="number" value="${bounds.max}">
      </div>
    `)
    .join("");
  el("safetyConfig").innerHTML = Object.entries(config.safety_limits || {})
    .map(([name, value]) => `
      <div class="config-row single">
        <div class="config-label">${labelFor(name)}</div>
        <input class="config-input" data-kind="safety" data-name="${escapeHtml(name)}" type="number" value="${value}">
      </div>
    `)
    .join("");
  el("weightConfig").innerHTML = Object.entries(config.objective_weights || {})
    .map(([name, value]) => `
      <div class="config-row single">
        <div class="config-label">${labelFor(name)}</div>
        <input class="config-input" data-kind="weight" data-name="${escapeHtml(name)}" type="number" step="0.05" min="0" value="${value}">
      </div>
    `)
    .join("");
}

function renderManifest() {
  const project = currentProject();
  const manifest = project?.manifest;
  const grid = el("manifestGrid");
  if (!manifest) {
    el("manifestType").textContent = "no plugin";
    grid.innerHTML = `<div class="manifest-card"><p>暂无插件声明。</p></div>`;
    return;
  }
  el("manifestType").textContent = manifest.type;
  grid.innerHTML = `
    <article class="manifest-card wide">
      <h3>${escapeHtml(manifest.name)}</h3>
      <p>${escapeHtml(manifest.description || "")}</p>
    </article>
    ${manifestCard("必需信号", manifest.required_signals)}
    ${manifestCard("可选信号", manifest.optional_signals)}
    ${manifestCard("动作参数", manifest.parameters)}
    ${manifestCard("输出指标", manifest.metrics)}
    ${manifestCard("插件实现", Object.entries(manifest.plugins || {}).map(([role, name]) => `${role}: ${name}`))}
    ${manifestCard("安全契约", manifest.safety_contract)}
  `;
}

function renderImportPreview() {
  const container = el("importPreview");
  const preview = state.importPreview;
  if (!preview) {
    container.innerHTML = "";
    return;
  }
  const status = preview.valid ? "字段校验通过" : "字段校验未通过";
  const statusClass = preview.valid ? "valid" : "invalid";
  container.innerHTML = `
    <div class="preview-box ${statusClass}">
      <div class="preview-head">
        <strong>${status}</strong>
        <span>${escapeHtml(preview.source_type)} · ${preview.rows} rows</span>
      </div>
      <div class="preview-groups">
        ${previewTokenGroup("必需", preview.required_signals)}
        ${previewTokenGroup("可选", preview.optional_signals)}
        ${previewTokenGroup("文件字段", preview.fieldnames)}
        ${previewTokenGroup("映射后字段", preview.mapped_fieldnames)}
        ${preview.missing?.length ? previewTokenGroup("缺失", preview.missing, "bad") : ""}
        ${preview.extra?.length ? previewTokenGroup("额外", preview.extra) : ""}
      </div>
      ${mappingEditor(preview)}
      ${preview.errors?.length ? `<ul class="preview-errors">${preview.errors.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}
      ${previewTable(preview)}
    </div>
  `;
}

function mappingEditor(preview) {
  const expected = [...(preview.required_signals || []), ...(preview.optional_signals || [])];
  if (!expected.length || !preview.fieldnames?.length) return "";
  return `
    <div class="mapping-grid">
      ${expected.map((signal) => `
        <label class="mapping-row">
          <span>${escapeHtml(labelFor(signal))}</span>
          <select data-field-map="${escapeHtml(signal)}">
            <option value="">不映射</option>
            ${preview.fieldnames.map((field) => `
              <option value="${escapeHtml(field)}" ${preview.field_mapping?.[signal] === field ? "selected" : ""}>${escapeHtml(field)}</option>
            `).join("")}
          </select>
        </label>
      `).join("")}
    </div>
  `;
}

function previewTokenGroup(title, items = []) {
  const tokens = Array.from(items || []);
  return `
    <div class="preview-group">
      <small>${escapeHtml(title)}</small>
      <div class="token-list">
        ${tokens.map((item) => `<span class="token">${escapeHtml(labelFor(item))}</span>`).join("") || "<p>无</p>"}
      </div>
    </div>
  `;
}

function previewTable(preview) {
  const rows = preview.preview_rows || [];
  const fields = preview.mapped_fieldnames || preview.fieldnames || [];
  if (!rows.length || !fields.length) return "";
  return `
    <div class="preview-table">
      <table>
        <thead><tr>${fields.map((field) => `<th>${escapeHtml(field)}</th>`).join("")}</tr></thead>
        <tbody>
          ${rows.map((row) => `<tr>${fields.map((field) => `<td>${escapeHtml(row[field] ?? "")}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function manifestCard(title, items = []) {
  const normalized = Array.from(items || []);
  return `
    <article class="manifest-card">
      <h3>${escapeHtml(title)}</h3>
      <div class="token-list">
        ${normalized.map((item) => `<span class="token">${escapeHtml(labelFor(item) || item)}</span>`).join("") || "<p>无</p>"}
      </div>
    </article>
  `;
}

function renderEvents() {
  const project = currentProject();
  const container = el("eventLog");
  if (!container) return;
  const events = [...(project?.events || [])].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))).slice(0, 14);
  if (!events.length) {
    container.innerHTML = `<p class="message">暂无实验日志。</p>`;
    return;
  }
  container.innerHTML = events
    .map((event) => `
      <div class="event-item">
        <div class="event-time">${formatTime(event.created_at)}</div>
        <div class="event-main">
          <strong>${escapeHtml(event.message)}</strong>
          <small>${escapeHtml(event.type)}</small>
        </div>
      </div>
    `)
    .join("");
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
  const series = uiFor(currentProject()).chart.filter((item) => points.some((point) => point[item.key] !== undefined));
  const scaleX = (value) => pad.left + ((value - minT) / Math.max(maxT - minT, 1e-12)) * plotW;
  series.forEach((item, index) => {
    const maxValue = Math.max(...points.map((p) => p[item.key]), 1);
    const scaleY = (value) => pad.top + plotH - (value / maxValue) * plotH;
    drawLine(ctx, points, scaleX, scaleY, item.key, item.color, index === 0 ? 2.4 : 2);
  });

  ctx.fillStyle = "#17201b";
  ctx.font = "12px Microsoft YaHei, sans-serif";
  series.forEach((item, index) => {
    ctx.fillStyle = item.color;
    ctx.fillText(item.label, pad.left + 8 + index * 86, pad.top + 16);
  });
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
  state.importPreview = null;
  await refresh();
  setMessage("演示闭环已生成。");
}

async function loadTrackDemo() {
  setMessage("正在载入轨道绝缘样例...");
  const bundle = await api("/api/demo/track", { method: "POST", body: "{}" });
  state.selectedProjectId = bundle.project.id;
  state.selectedRunId = bundle.runs.at(-1)?.id || null;
  state.importPreview = null;
  await refresh();
  setMessage("轨道绝缘样例已生成。");
}

async function createBlankProject() {
  const experimentType = el("newProjectType").value || "sic_gan_switching";
  const experiment = state.experiments.find((item) => item.type === experimentType);
  const name = el("newProjectName").value.trim() || `${experiment?.name || "实验"}项目`;
  setMessage("正在创建空白项目...");
  const bundle = await api("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      name,
      experiment_type: experimentType,
      description: "从插件 manifest 创建的空白项目。",
    }),
  });
  state.selectedProjectId = bundle.project.id;
  state.selectedRunId = null;
  state.importPreview = null;
  el("newProjectName").value = "";
  await refresh();
  setMessage("空白项目已创建，可先下载模板再导入 run。");
}

function downloadTemplate() {
  const experimentType = el("newProjectType").value;
  if (!experimentType) {
    setMessage("请先选择实验类型。");
    return;
  }
  window.location.href = `/api/templates/${encodeURIComponent(experimentType)}.csv`;
  setMessage("CSV 模板下载已开始。");
}

async function createRecommendation() {
  const project = currentProject();
  if (!project) return setMessage("请先载入或创建项目。");
  setMessage("正在生成参数推荐...");
  await api("/api/recommendations", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      optimizer: el("optimizerSelect").value,
    }),
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
  const preview = await previewData();
  if (!preview?.valid) {
    renderImportPreview();
    return setMessage("数据校验未通过，请先修正字段后再导入。");
  }
  setMessage("正在导入并计算指标...");
  const content = await file.text();
  const dataset = await api("/api/datasets/import", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      filename: file.name,
      content,
      field_mapping: collectFieldMapping(),
    }),
  });
  const run = await api("/api/runs", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      dataset_id: dataset.id,
      label: el("runLabel").value || file.name,
      parameters: collectRunParams(),
    }),
  });
  state.selectedRunId = run.id;
  state.importPreview = null;
  await refresh();
  setMessage("run 已记录。");
}

async function simulateRun() {
  const project = currentProject();
  if (!project) return setMessage("请先载入或创建项目。");
  setMessage("正在运行数字孪生仿真...");
  const run = await api("/api/runs/simulate", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      label: el("runLabel").value || "simulation",
      parameters: collectRunParams(),
      mode: el("modelModeSelect").value,
    }),
  });
  state.selectedRunId = run.id;
  state.importPreview = null;
  await refresh();
  setMessage("仿真 run 已生成。");
}

async function verifyRecommendation(recommendationId) {
  const project = currentProject();
  if (!project) return setMessage("请先载入或创建项目。");
  setMessage("正在仿真验证推荐参数...");
  const run = await api("/api/recommendations/simulate", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      recommendation_id: recommendationId,
      mode: el("modelModeSelect").value,
    }),
  });
  state.selectedRunId = run.id;
  await refresh();
  setMessage("推荐参数已完成仿真验证。");
}

async function calibrateModel() {
  const project = currentProject();
  if (!project) return setMessage("请先载入或创建项目。");
  setMessage("正在根据最新导入 run 校准模型...");
  await api("/api/models/calibrate", {
    method: "POST",
    body: JSON.stringify({ project_id: project.project.id }),
  });
  await refresh();
  setMessage("模型校准已保存为新配置版本。");
}

async function previewData() {
  const project = currentProject();
  const file = el("dataFile").files[0];
  if (!project) {
    setMessage("请先载入或创建项目。");
    return null;
  }
  if (!file) {
    setMessage("请选择 CSV 或 JSON 文件。");
    return null;
  }
  setMessage("正在预览并校验数据...");
  const content = await file.text();
  const preview = await api("/api/datasets/preview", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      filename: file.name,
      content,
      field_mapping: collectFieldMapping(),
    }),
  });
  state.importPreview = preview;
  renderImportPreview();
  setMessage(preview.valid ? "数据校验通过，可以导入 run。" : "数据校验未通过。");
  return preview;
}

function collectFieldMapping() {
  const mapping = {};
  document.querySelectorAll("[data-field-map]").forEach((select) => {
    if (select.value) {
      mapping[select.dataset.fieldMap] = select.value;
    }
  });
  return mapping;
}

function collectRunParams() {
  const params = {};
  document.querySelectorAll("[data-run-param]").forEach((input) => {
    params[input.dataset.runParam] = Number(input.value);
  });
  return params;
}

async function saveConfig() {
  const project = currentProject();
  if (!project?.config) return setMessage("请先载入或创建项目。");
  const nextConfig = structuredClone(project.config);

  document.querySelectorAll("[data-kind='param-min']").forEach((input) => {
    const name = input.dataset.name;
    nextConfig.parameter_space[name].min = Number(input.value);
  });
  document.querySelectorAll("[data-kind='param-max']").forEach((input) => {
    const name = input.dataset.name;
    nextConfig.parameter_space[name].max = Number(input.value);
  });
  document.querySelectorAll("[data-kind='safety']").forEach((input) => {
    nextConfig.safety_limits[input.dataset.name] = Number(input.value);
  });
  document.querySelectorAll("[data-kind='weight']").forEach((input) => {
    nextConfig.objective_weights[input.dataset.name] = Number(input.value);
  });

  setMessage("正在保存配置版本...");
  await api("/api/configs/update", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project.id,
      config: {
        parameter_space: nextConfig.parameter_space,
        safety_limits: nextConfig.safety_limits,
        objective_weights: nextConfig.objective_weights,
      },
    }),
  });
  await refresh();
  setMessage("配置版本已保存。");
}

function setMessage(text) {
  el("message").textContent = text;
}

function format(value, unit = "") {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return `${Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 4 })}${unit}`;
}

function formatMetric(key, value, unit = "") {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  if (key === "risk_level") return value;
  if (key === "overshoot_ratio") return `${(Number(value) * 100).toFixed(2)}%`;
  if (key === "ringing_frequency") return `${(Number(value) / 1_000_000).toFixed(2)} MHz`;
  if (key === "degradation_index") return Number(value).toFixed(3);
  return format(value, unit);
}

function uiFor(project) {
  const type = project?.project?.experiment_type || "sic_gan_switching";
  return EXPERIMENT_UI[type] || EXPERIMENT_UI.sic_gan_switching;
}

function round(value) {
  return Math.round(Number(value) * 10000) / 10000;
}

function formatTime(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function labelFor(key) {
  const labels = {
    dead_time: "死区时间",
    gate_resistance: "栅极电阻",
    drive_voltage: "驱动电压",
    damping_resistance: "阻尼电阻",
    test_voltage: "测试电压",
    detection_period: "检测周期",
    alarm_threshold: "报警阈值",
    max_vds: "最大 Vds",
    max_ids: "最大 Ids",
    max_temperature: "最高温度",
    max_test_voltage: "最高测试电压",
    min_insulation_mohm: "最低绝缘",
    max_leakage_ma: "最大泄漏",
    max_humidity: "最高湿度",
    avg_insulation_mohm: "平均绝缘",
    overshoot_ratio: "过冲权重",
    settling_time_us: "衰减权重",
    switching_loss_estimate: "损耗权重",
    degradation_index: "退化权重",
    environment_stress: "环境权重",
  };
  return labels[key] || key;
}

el("loadDemo").addEventListener("click", () => loadDemo().catch((error) => setMessage(error.message)));
el("loadTrackDemo").addEventListener("click", () => loadTrackDemo().catch((error) => setMessage(error.message)));
el("createProjectBtn").addEventListener("click", () => createBlankProject().catch((error) => setMessage(error.message)));
el("downloadTemplateBtn").addEventListener("click", () => downloadTemplate());
el("recommendBtn").addEventListener("click", () => createRecommendation().catch((error) => setMessage(error.message)));
el("calibrateModelBtn").addEventListener("click", () => calibrateModel().catch((error) => setMessage(error.message)));
el("reportBtn").addEventListener("click", () => generateReport().catch((error) => setMessage(error.message)));
el("previewDataBtn").addEventListener("click", () => previewData().catch((error) => setMessage(error.message)));
el("importRunBtn").addEventListener("click", () => importRun().catch((error) => setMessage(error.message)));
el("simulateRunBtn").addEventListener("click", () => simulateRun().catch((error) => setMessage(error.message)));
el("saveConfigBtn").addEventListener("click", () => saveConfig().catch((error) => setMessage(error.message)));
el("dataFile").addEventListener("change", () => {
  state.importPreview = null;
  renderImportPreview();
});
el("runPicker").addEventListener("change", (event) => {
  state.selectedRunId = event.target.value;
  render();
});
document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-verify-rec]");
  if (target) {
    verifyRecommendation(target.dataset.verifyRec).catch((error) => setMessage(error.message));
  }
});
window.addEventListener("resize", () => drawChart(currentRun()));

refresh().catch((error) => setMessage(error.message));
