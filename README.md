# Industrial Vision Workflows

面向工业视频动作研究和点云几何诊断的本地工作流扩展。四个核心组件是 **Profiles、Skills、Experiment Engine、Evaluation Engine**；Workflow 将它们与固定版本的 **LoopForge Portable** 组合。LoopForge 是唯一流程状态机。

## 目录与架构

| 路径 | 用途 |
|---|---|
| `profiles/` | SOP Research、SOP Product、Pointcloud 3D 三种专业上下文 |
| `skills/` | 七项可单独调用或按阶段注入的专业技能 |
| `workflows/` | 四条路线，映射原生 REQUIREMENT 到 SUMMARY 阶段 |
| `engines/experiment-engine/` | 固定数据版本、runner、配置、模型及实际进程记录 |
| `engines/evaluation-engine/` | 从独立真值计算检测、事件、中心误差和 trace 性能指标 |
| `ivw/`、`ivw.py` | 安装、只读接入和原生状态命令的薄适配层 |
| `agents/`、`checks/` | 专业职责映射及十项按需检查模块 |
| `examples/`、`tests/`、`scripts/` | 合成示例、标准库测试、Windows 交付与 Smoke |
| `vendor/loopforge/` | 按 `upstream.lock.json` 逐文件校验的固定上游，禁止修改 |

Python 3.10+，无需第三方 Python 依赖；Smoke 还需要 Git，Windows 脚本使用 PowerShell。本次验证使用 Windows / Python 3.12。业务项目位置见 `config/protection.json`，接入文档路径见 `examples/projects/`。其他机器应先配置自己的本地路径。

## 安装与工作流准备

从扩展根目录运行；路径包含空格或中文时加引号：

```powershell
python ivw.py validate
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Install.ps1 -Project "workspaces/sop"
python ivw.py status --project "workspaces/sop"
python ivw.py doctor --project "workspaces/sop"
python ivw.py init --project "workspaces/sop" --slug baseline --profile sop-research --workflow sop-model-research --example sop
python ivw.py prepare --state "workspaces/sop/artifacts/baseline/workflow-state.json" --stage REQUIREMENT --request "比较动作事件基线与候选"
```

`industrial/REQUIREMENT-prompt.md` 包含实际领域正文。REQUIREMENT 报告必须由用户明确确认；本工具不会代批。后续独立 Agent 的派发和原生 `assign/start/finish` 用法见 [Codex 适配说明](adapters/codex/README.md)。`init/prepare` 只准备工作流，不会自动运行训练。

## 基础实验与评测闭环

```powershell
python ivw.py experiment run --config examples/experiments/calibration-baseline.json --store local/experiments
python ivw.py experiment run --config examples/experiments/calibration-candidate.json --store local/experiments
python ivw.py evaluate --run "<run.json 路径>" --dataset examples/datasets/calibration.json --protocol examples/evaluation-protocol.json --store local/experiments
python ivw.py evaluate --baseline "<基线 report.json>" --candidate "<候选 report.json>"
```

每次 run 返回唯一记录路径；分别评测基线与候选后再比较。评测退出码：`0` 通过、`1` 不达标、`2` 输入或完整性错误。实验失败/超时退出 `1`，仍保留日志和记录。

示例均为 **synthetic**：标定候选只用 train 标签估计偏移，独立 test 中心误差由约 0.12 m 降至浮点精度附近；SOP 候选虽然召回提高，但证据绑定错误会被拒绝。不是实际视觉模型训练或现场验收。完整接口与限制见 [引擎契约](docs/engine-contracts.md)。

## 验证、共享与卸载

```powershell
python -m unittest discover -s tests -v
python scripts/smoke_test.py
python ivw.py validate
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Share.ps1 -Output "dist/industrial-vision-workflows.zip"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Uninstall.ps1 -Project "workspaces/sop"
```

Smoke 留存 `local/smoke-*/report.json`，包含实验、独立评测、失败记录、四条路线门禁、Windows 脚本及共享包搬迁验证。共享包按 `config/share-files.json` 和上游锁定清单打包，附逐文件 SHA-256；不包含本地状态、客户数据或权重。ZIP 输出已存在时拒绝覆盖。卸载保留用户改过的文件和实验/工作流产物。

## 开发边界

Python 使用四空格缩进、`snake_case` 命名，测试为 `unittest` 的 `tests/test_*.py`。修改后运行上述三项标准验证。现有业务项目只读，不在其目录安装或输出产物，不切分支、stash、提交或 Push。本项目 Push 也需要用户明确批准。

runner 是受信任的本地 Python 程序；独立工作目录不构成安全沙箱。只对已审阅程序执行 `experiment register-runner`。评测不用 runner 自报分数；模拟、离线与现场证据分别报告，任何 PASS 都不产生生产或装载授权。

进度与证据见 [架构计划](docs/architecture-and-plan.md)、[实现报告](docs/implementation-report.md)。
