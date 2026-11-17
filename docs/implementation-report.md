# P0/P1 与基础评测闭环实现报告

日期：2026-11-17。按 [既定架构计划](architecture-and-plan.md) 完成 P0/P1 交付，并实现、运行和测试 P2 的基础确定性评测闭环。以下结论以本次实际命令为依据。

## 交付范围

| 范围 | 结果与证据 |
|---|---|
| P0 固定上游 | `69e4bf093cf26dc72a2b0bc5d7452f86ce96f660`，514 个文件 SHA-256 校验通过，未编辑 vendor |
| P0 专业组件 | 3 Profiles、7 Skills、4 Workflows、3 角色、10 检查模块；目录、引用及阶段/引擎映射校验通过 |
| P0 Portable 适配 | 新目录安装、status、doctor、四条路线 init/prepare/validate 通过；REQUIREMENT 未确认时不能进入 DESIGN |
| P0 Windows 交付 | Install/Share/Uninstall 脚本实际执行；中文及空格路径可用；冲突不覆盖，卸载保留用户修改和工作流产物 |
| P1 实验引擎 | 数据版本与分组审计、固定 runner、独立工作目录、训练/推理进程、模型登记、失败/超时、摘要校验和版本对比通过 |
| P1 只读接入 | SOP 和鞍座文档以本地引用及摘要接入，新工作区写产物，源项目不安装技能或输出文件 |
| 基础评测 | 独立读取固定真值，计算检测/事件/点云与 trace 指标；门槛、缺失预测、空场、样本量、UNKNOWN 和证据绑定检查通过 |
| 合成闭环 | 8 组基线/候选实验、8 份独立评测、4 组对比及失败留档；共享包搬迁后再次运行标定实验及评测通过 |

四大组件仍为 Profiles、Skills、Experiment Engine、Evaluation Engine；Workflow 组合它们与唯一状态机 LoopForge Portable。未引入 Classic 或第二套状态。

## 本轮修复与实现

- 修复安装新路径前未创建目录导致的两个原有集成测试失败；修复 CLI `init --example` 参数未注册的问题。
- 完善组件校验、固定输入/配置/权重变更检查、相对模型引用解析和已完成实验的预测摘要约束。
- 评测强制检查预测覆盖、正整数样本下限和负例下限；未确认标注不能作为负例。补充空场误报率、未评估项、覆盖及命令/代码/模型来源。
- 缺失 trace 保持 null；非法 trace、协议、非有限数值与路径穿越被拒绝。安装与卸载不覆盖用户文件，禁止写入受保护源项目和 vendor。
- 新增白名单共享包、逐文件包清单和搬迁验证。首次搬迁测试发现共享清单漏带 workflows，已修复并通过最终回归。
- 补齐 README、引擎契约、Smoke 和本报告；原有 AGENTS.md 保持原样。

## 实际验证

| 命令 | 结果 |
|---|---|
| `python -m unittest discover -s tests -v` | **passed，51 tests，57.597 秒** |
| `python scripts/smoke_test.py` | **passed，56 次实际子命令调用**，包含预期拒绝/FAIL 的退出码验证 |
| `python ivw.py validate` | **passed**，514 个上游文件及全部组件验证 |
| `python ivw.py status` | **passed**，Portable 90 个受管文件 changed=0、missing=0，extension_drift=[] |
| `python ivw.py doctor` | **passed**，assets and installations are healthy |

单元测试覆盖原生命令集成、只读保护、安装冲突与卸载保留、数据泄漏、实际失败与超时、训练产物、独立评分、重复匹配、错误真值版本、篡改产物、缺失空场预测、无负例、样本不足、未知性能和非法输入。

本地验证记录：

- [测试日志](../local/unit-tests-p0p1-final.log)
- [Smoke 报告](../local/smoke-aab948007c3d4d198d1cc9897bf87e44/report.json)，含具体 run/evaluation 路径及命令 stdout/stderr 日志
- [Smoke 前状态](../local/smoke-aab948007c3d4d198d1cc9897bf87e44/protected-before.json)、[Smoke 后状态](../local/smoke-aab948007c3d4d198d1cc9897bf87e44/protected-after.json)

这些 local 证据保留在本机，不进入共享包。三个 Git 源项目的 HEAD/status/diff 及五份接入文档摘要前后一致；两个非 Git 根目录只核对存在状态及所引用文档，不宣称完整文件树审计。

## 合成评测观察

| 示例 | 版本 | Precision | Recall | 附加观察 | 结论 |
|---|---|---:|---:|---|---|
| SOP 事件 | baseline | 1.00 | 0.80 | Evidence Binding 1.00 | PASS |
| SOP 事件 | candidate | 1.00 | 1.00 | Evidence Binding 0.80 | **FAIL** |
| 检测 | baseline | 1.00 | 1.00 | FP=0 | PASS |
| 检测 | candidate | 0.80 | 1.00 | FP=1，空场误报率 0.50 | PASS，仍报告退化 |
| 鞍座中心 | baseline | 0.75 | 0.60 | 匹配中心最大误差约 0.03 m | **FAIL** |
| 鞍座中心 | candidate | 0.80 | 0.80 | 仍有 FP=1、FN=1 | PASS，仅达到示例门槛 |
| 合成标定 | baseline | 1.00 | 1.00 | 最大中心误差约 0.12 m | **FAIL** |
| 合成标定 | candidate | 1.00 | 1.00 | 最大中心误差约 8.9e-16 m | PASS |

标定训练只用 4 个 train 组估计平移偏差，test 有 4 个目标样本及 1 个空场。SOP 的错误证据样本实际进入 failure 记录。检测候选虽然达到示例门槛，比较报告仍显示 precision 退化；工具不自动选型或晋级。

## 共享与边界

源码共享清单为 99 个扩展文件，加 514 个固定上游文件，共 613 个 payload 文件；ZIP 另附 PACKAGE-MANIFEST.json 的逐文件 SHA-256。交付入口为 `scripts/Share.ps1`，固定交付名为 `dist/industrial-vision-workflows-p0p1.zip`。共享包排除 local、workspaces、安装状态、客户原始数据和权重；新机器需调整本地接入路径。

此次实现、自查与测试均由当前 Agent 执行；独立 Agent 审查为 **not-run**，完整七阶段多 Agent 交付流程为 **not-run**。Smoke 只验证原生准备、状态校验和拒绝门禁，没有创建虚构 executor ID 或批准 REQUIREMENT。

证据等级全部为 **synthetic**，真实客户数据离线评测和现场验证均为 **not-run**。标定是标准库合成示例，不是真实视觉模型训练；检测不是 mAP，事件绑定不证明物理完成，几何不覆盖配组/尺寸，性能不是独立硬件采样或长稳资格。P2 全量、P3 真实专项闭环及 OCR/分割仍属于后续范围；production_authorized 与 loading_authorized 保持 false。

P0/P1 验收阶段没有对任何业务项目切分支、stash、提交或 Push，也未对本项目执行 Push。后续 GitHub 发布以用户明确授权和远端实际提交为准；上述验证结论不包含远端 CI。
