# 实验室自适应优化验证平台 MVP

这是根据 `MVP_PRD.md` 和 `TECH_PLAN.md` 启动的第一版本地原型。当前版本聚焦 SiC/GaN 关断振荡优化闭环。

## 当前能力

- 一键载入 SiC/GaN 演示项目。
- 导入 CSV / JSON 波形数据。
- 自动提取 Vds 峰值、Ids 峰值、过冲比例、振荡频率、衰减时间、开关损耗估计和风险等级。
- 基于历史 run 生成下一组参数推荐。
- 对推荐参数执行安全约束检查。
- 生成 HTML 实验报告。
- 提供本地 Web 工作台。

## 启动

```powershell
python .\app.py
```

打开：

```text
http://127.0.0.1:8765
```

进入页面后点击“载入演示”，系统会自动创建项目、导入两组样例数据、计算指标、生成推荐和报告。

## 测试

```powershell
python -m unittest discover -s tests
```

## 数据格式

CSV 至少需要以下字段：

```text
time,vgs,vds,ids
```

可选字段：

```text
temperature
```

样例数据在 `sample_data/` 目录中。

## 目录结构

```text
app.py                  本地 HTTP 服务入口
src/lab_mvp/            后端核心模块
static/                 前端工作台
sample_data/            SiC/GaN 样例数据
data/                   本地运行数据和报告
tests/                  单元测试
```

## 下一步

- 增加更稳定的波形指标算法。
- 增加贝叶斯优化插件。
- 增加轨道绝缘检测样例插件。
- 增加配置编辑页面。
- 增加 PDF 导出。

