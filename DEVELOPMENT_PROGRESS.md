# 开发进度

更新时间：2026-05-01

## 当前结论

MVP 本地实验闭环已全面完成。平台现在可以在本地单机运行，完成项目创建、数据导入、字段映射、指标提取、参数推荐、安全校验、人工确认、仿真验证、模型校准、报告生成、事件追踪、项目导出和插件管理。

外部插件包机制已扩展到全部 6 种类型（`optimizer`、`feature`、`model`、`constraint`、`report`、`data_source`），支持热重载 API 和浏览器打印报告，工作台面板支持折叠。

完整愿景中的真实设备采集、SPICE / Simscape 运行时、正式 RL 训练、权限控制和社区插件市场仍属于后续集成阶段。

## 已完成

- 本地 HTTP 服务：`app.py`
- 本地 JSON store：`data/store.json`
- 单屏前端工作台：`static/index.html`、`static/app.js`、`static/styles.css`
- 启停脚本：`scripts/start.sh`、`scripts/stop.sh`、`scripts/test.sh`
- 日志输出：`logs/server.log`（按天轮转，保留 14 天）
- 两类实验类型：
  - `sic_gan_switching`
  - `track_insulation`
- 实验 manifest：
  - 信号定义
  - 字段别名
  - 参数空间
  - 指标定义
  - 插件声明
  - 安全契约
- 数据导入：
  - CSV
  - JSON
  - HDF5 可选适配器
  - CSV 模板下载
  - 导入前预览
  - 自动字段映射
  - 手动字段映射
- 数据预处理：
  - 行数扫描
  - 异常扫描
  - 噪声指数
  - 信号统计
- 指标提取：
  - SiC/GaN 关断振荡指标
  - 轨道绝缘检测指标
- 数字孪生：
  - SiC/GaN 轻量模型
  - 轨道绝缘轻量模型
  - `fast` / `high_fidelity` 两种模式
- 优化推荐：
  - 启发式优化器
  - 轻量贝叶斯式优化器
  - 外部保守优化器样例包
- 安全约束：
  - 参数边界检查
  - 风险阈值检查
  - 危险组合检查
  - 安全拒绝原因
- 人机闭环：
  - 推荐接受
  - 推荐拒绝
  - 推荐仿真验证
- 在线校准：
  - 基于最新真实导入 run 与模型预测的比例校准
  - 自动生成新配置版本
- 报告与导出：
  - HTML 报告（含打印为 PDF 按钮，`@media print` 优化）
  - 项目 JSON 导出
  - 事件日志 CSV 导出
- 插件管理：
  - 运行时加载 / 卸载
  - 插件状态持久化
  - 卸载后阻断相关流程
  - 前端插件目录操作
  - 外部插件包扫描（热重载 API `POST /api/plugins/reload`）
- 外部插件包格式：
  - `plugins/<package>/plugin.json`
  - `plugins/<package>/plugin.py`
  - 支持全部 6 种类型：`optimizer`、`feature`、`model`、`constraint`、`report`、`data_source`
- 前端可折叠面板：
  - config / manifest / event / plugin 四个面板支持折叠
  - 折叠状态持久化到 `localStorage`

## 外部插件包

已提供样例：

```text
plugins/
  conservative_optimizer/
    plugin.json
    plugin.py
```

当前支持的外部插件类型及必须实现的方法：

| 类型 | 必须方法 |
| --- | --- |
| `optimizer` | `recommend(runs, config)` |
| `feature` | `extract(rows, config)` |
| `model` | `simulate(parameters, config, mode)` |
| `constraint` | `check(recommendation, config)` |
| `report` | `generate(project, runs, recommendations, config, manifest, events)` |
| `data_source` | `load_text(content, signals, field_mapping)` + `preview_text(content, ...)` |

`data_source` 类型需在 `plugin.json` 中额外声明 `file_extensions`：

```json
{
  "type": "data_source",
  "file_extensions": [".tsv", ".dat"],
  ...
}
```

## 验证记录

最近通过的验证：

```bash
bash scripts/test.sh
```

当前测试覆盖数量：27 条。

覆盖范围：

- 核心闭环
- 双实验类型
- 数据预览
- 字段映射
- 数字孪生
- 推荐仿真
- 模型校准
- 插件目录
- 动态加载 / 卸载
- 外部插件包扫描
- 推荐人工决策
- 项目导出
- 事件导出
- HDF5 可选适配器

## 已知边界

- HDF5 解析依赖可选 `h5py`，未安装时会返回清晰错误。
- 真实 SPICE / Simscape 未接入。
- 真实实验设备采集未接入。
- PDF 报告以浏览器打印为主，未实现后端 PDF 生成库。
- 权限系统未实现。
- 社区插件市场未实现。
- RL 实时训练 / 控制未实现。

## 建议下一步

1. 增加真实数据采集适配器（串口、文件夹监听、HTTP 数据源），以 `data_source` 外部插件接入。
2. 增加真实 SPICE / Simscape 适配层，以 `model` 外部插件接入。
3. 提供更多外部插件包样例（`feature`、`model`、`report` 类型）。
4. 增加插件包 CLI 校验工具，例如 `python -m lab_mvp.plugins validate plugins/<package>`。

## 运行方式

```bash
bash scripts/start.sh
```

访问：

```text
http://127.0.0.1:8765
```
