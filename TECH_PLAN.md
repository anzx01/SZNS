# 实验室自适应优化验证平台技术开发计划

## 1. 技术目标

本计划用于指导 MVP 开发。第一阶段以 SiC/GaN 关断振荡优化为主场景，构建一套可扩展的实验闭环平台。

核心技术目标：

- 建立实验编排核心。
- 建立统一数据模型。
- 支持波形数据导入和指标提取。
- 支持小样本参数推荐。
- 支持安全约束校验。
- 支持实验记录、对比和报告生成。
- 建立最小可用插件协议。

## 2. 建议系统架构

系统建议拆分为以下模块：

```text
UI Layer
  -> Experiment API
  -> Experiment Orchestrator
     -> Data Layer
     -> Feature Layer
     -> Optimization Layer
     -> Safety Layer
     -> Report Layer
  -> Storage Layer
```

### 2.1 Experiment Orchestrator

实验编排器是系统核心，负责串联完整流程。

职责：

- 创建实验。
- 创建 run。
- 管理 run 状态。
- 调用数据插件。
- 调用特征插件。
- 调用优化插件。
- 调用安全约束插件。
- 保存结果。
- 触发报告生成。

推荐状态机：

```text
created
configured
ready
running
completed
failed
paused
```

### 2.2 Data Layer

职责：

- 文件上传。
- CSV / JSON 解析。
- 字段映射。
- 数据校验。
- 数据集版本管理。

第一版数据字段：

```text
time
vgs
vds
ids
temperature
```

### 2.3 Feature Layer

职责：

- 对波形数据进行特征提取。
- 保存指标结果。
- 向优化器提供目标值。
- 向 UI 和报告层提供图表数据。

核心指标：

```text
max_vds
max_ids
overshoot_ratio
ringing_frequency
settling_time_us
switching_loss_estimate
risk_level
```

### 2.4 Optimization Layer

第一版推荐算法：

- 启发式规则。
- 网格搜索。
- 贝叶斯优化，视依赖和样本量决定是否在 MVP 中启用。

不建议第一版实现实时 RL 控制。

### 2.5 Safety Layer

职责：

- 检查参数边界。
- 检查输出指标风险。
- 检查危险参数组合。
- 拒绝不安全推荐。
- 输出拒绝原因。

安全层必须位于优化器之后、执行确认之前。

### 2.6 Report Layer

职责：

- 生成 HTML 报告。
- 汇总项目、run、参数、指标、图表和推荐记录。
- 后续可扩展 PDF 导出。

## 3. 核心数据模型

### 3.1 ExperimentProject

```json
{
  "id": "project_001",
  "name": "SiC/GaN 关断振荡优化",
  "experiment_type": "sic_gan_switching",
  "description": "",
  "created_at": "",
  "updated_at": ""
}
```

### 3.2 ExperimentConfig

```json
{
  "id": "config_001",
  "project_id": "project_001",
  "parameter_space": {
    "dead_time": { "min": 50, "max": 500, "unit": "ns" },
    "gate_resistance": { "min": 1, "max": 20, "unit": "ohm" },
    "drive_voltage": { "min": 12, "max": 18, "unit": "V" }
  },
  "safety_limits": {
    "max_vds": 900,
    "max_ids": 50,
    "max_temperature": 100
  },
  "objective_weights": {
    "overshoot_ratio": 0.4,
    "settling_time_us": 0.3,
    "switching_loss_estimate": 0.3
  }
}
```

### 3.3 Dataset

```json
{
  "id": "dataset_001",
  "project_id": "project_001",
  "source_type": "csv",
  "file_path": "",
  "field_mapping": {
    "time": "time",
    "vgs": "vgs",
    "vds": "vds",
    "ids": "ids"
  },
  "created_at": ""
}
```

### 3.4 ExperimentRun

```json
{
  "id": "run_001",
  "project_id": "project_001",
  "config_id": "config_001",
  "dataset_id": "dataset_001",
  "status": "completed",
  "parameters": {
    "dead_time": 120,
    "gate_resistance": 5,
    "drive_voltage": 15
  },
  "metrics": {},
  "created_at": "",
  "completed_at": ""
}
```

### 3.5 Recommendation

```json
{
  "id": "rec_001",
  "project_id": "project_001",
  "source_run_ids": ["run_001", "run_002"],
  "recommended_parameters": {
    "dead_time": 140,
    "gate_resistance": 6,
    "drive_voltage": 15
  },
  "expected_improvement": {
    "overshoot_ratio": "-8%",
    "settling_time_us": "-5%"
  },
  "safety_result": {
    "passed": true,
    "reasons": []
  },
  "status": "pending_user_confirmation"
}
```

## 4. 插件协议

第一版插件可以用接口或抽象类实现，不需要复杂动态加载。

### 4.1 Plugin Manifest

```json
{
  "name": "sic_gan_switching",
  "version": "0.1.0",
  "plugin_type": "experiment",
  "description": "SiC/GaN switching oscillation optimization plugin",
  "parameters": ["dead_time", "gate_resistance", "drive_voltage"],
  "signals": ["time", "vgs", "vds", "ids"],
  "metrics": ["max_vds", "overshoot_ratio", "ringing_frequency"]
}
```

### 4.2 DataSourcePlugin

```python
class DataSourcePlugin:
    def load(self, source):
        raise NotImplementedError

    def validate(self, dataset):
        raise NotImplementedError
```

### 4.3 FeaturePlugin

```python
class FeaturePlugin:
    def extract(self, dataset, config):
        raise NotImplementedError
```

### 4.4 OptimizerPlugin

```python
class OptimizerPlugin:
    def recommend(self, runs, config):
        raise NotImplementedError
```

### 4.5 ConstraintPlugin

```python
class ConstraintPlugin:
    def check(self, recommendation, config):
        raise NotImplementedError
```

### 4.6 ReportPlugin

```python
class ReportPlugin:
    def generate(self, project, runs, recommendations):
        raise NotImplementedError
```

## 5. 第一版内置插件

必须实现：

- `CSVDataSourcePlugin`
- `JSONDataSourcePlugin`
- `SiCGaNFeaturePlugin`
- `HeuristicOptimizerPlugin`
- `SiCGaNConstraintPlugin`
- `HTMLReportPlugin`

可选实现：

- `BayesianOptimizerPlugin`
- `TrackInsulationDemoPlugin`
- `PDFReportPlugin`

## 6. 推荐开发阶段

### Phase 0：需求冻结与样例数据准备，3 天

任务：

- 明确 SiC/GaN 字段定义。
- 准备样例 CSV 数据。
- 明确安全阈值默认值。
- 明确第一版指标算法。
- 固化 MVP 验收标准。

产出：

- 样例数据文件。
- 字段说明文档。
- 指标定义文档。
- 安全阈值配置样例。

### Phase 1：后端基础与数据模型，1 周

任务：

- 搭建项目结构。
- 实现核心数据模型。
- 实现实验项目 CRUD。
- 实现实验 run CRUD。
- 实现 CSV / JSON 导入。
- 实现本地存储。

验收：

- 可以创建项目。
- 可以导入数据。
- 可以生成 run 记录。

### Phase 2：特征提取，1 周

任务：

- 实现波形解析。
- 实现峰值计算。
- 实现过冲比例计算。
- 实现振荡频率估算。
- 实现衰减时间估算。
- 实现风险等级判断。

验收：

- 导入数据后能自动生成指标。
- 指标能被 API 查询。
- 异常数据能给出错误提示。

### Phase 3：优化推荐与安全约束，1.5 周

任务：

- 实现参数空间配置。
- 实现启发式优化器。
- 实现安全约束检查。
- 实现推荐记录。
- 实现人工确认状态。
- 可选实现贝叶斯优化。

验收：

- 可以基于历史 run 生成推荐。
- 不安全推荐会被拒绝。
- 推荐结果包含原因和预期改进方向。

### Phase 4：前端界面，2 周

页面：

- 项目列表页。
- 实验配置页。
- 数据导入页。
- 波形与指标页。
- 参数推荐页。
- 实验对比页。
- 报告预览页。

验收：

- 用户可以从 UI 完成一次完整实验流程。
- 可以查看波形、指标、推荐参数和安全结果。

### Phase 5：报告生成与闭环集成，1 周

任务：

- 实现 HTML 报告。
- 实现实验对比报告。
- 集成完整流程。
- 补齐错误处理。
- 补齐基础测试。

验收：

- 完成“导入数据 -> 提取指标 -> 推荐参数 -> 安全检查 -> 记录结果 -> 生成报告”的闭环。

### Phase 6：第二场景插件验证，1 周

任务：

- 定义轨道绝缘检测插件 manifest。
- 实现最小字段映射。
- 实现简单指标提取。
- 验证核心编排器无需大改。

验收：

- 新增实验类型不需要修改核心编排器。
- 插件协议能支撑第二类实验雏形。

## 7. 推荐里程碑

| 里程碑 | 时间 | 结果 |
| --- | --- | --- |
| M1 | 第 1 周末 | 项目、run、数据导入跑通 |
| M2 | 第 2 周末 | SiC/GaN 指标提取跑通 |
| M3 | 第 4 周中 | 推荐与安全约束跑通 |
| M4 | 第 6 周中 | 前端主流程跑通 |
| M5 | 第 7 周末 | 报告与闭环完成 |
| M6 | 第 8 周末 | 第二插件样例完成 |

## 8. 测试计划

### 单元测试

- CSV / JSON 解析。
- 字段映射。
- 指标计算。
- 安全约束检查。
- 优化器推荐逻辑。

### 集成测试

- 数据导入到指标提取。
- 指标提取到参数推荐。
- 参数推荐到安全校验。
- 完整 run 生命周期。
- 报告生成。

### 样例数据测试

至少准备：

- 正常波形样例。
- 高过冲样例。
- 高振荡样例。
- 缺失字段样例。
- 越界参数样例。

## 9. 技术风险与应对

### 风险 1：指标算法不够稳定

应对：

- 第一版先使用规则算法。
- 保留人工修正入口。
- 用样例数据建立回归测试。

### 风险 2：优化推荐可信度不足

应对：

- 先输出候选参数和推荐理由。
- 不做自动设备控制。
- 使用安全层和人工确认降低风险。

### 风险 3：插件接口过度设计

应对：

- 第一版只实现抽象接口。
- 先通过两个实验类型验证接口。
- 暂不做复杂动态加载。

### 风险 4：真实实验安全风险

应对：

- 优化器不得绕过安全层。
- 所有推荐必须人工确认。
- 推荐参数、拒绝原因和确认动作全部留痕。

## 10. 开发优先级

### P0

- 实验编排器。
- 数据模型。
- CSV / JSON 导入。
- SiC/GaN 特征提取。
- 安全约束。
- run 记录。

### P1

- 参数推荐。
- 波形可视化。
- 实验对比。
- HTML 报告。
- 插件 manifest。

### P2

- 贝叶斯优化。
- 轨道绝缘检测样例。
- PDF 导出。
- 更复杂的插件加载。

### 暂不排期

- 强化学习实时控制。
- 设备无人值守控制。
- 社区插件市场。
- 云端多租户。

