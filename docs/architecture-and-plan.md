# 架构与实施计划

制定日期：2026-11-17。范围：独立工业视觉工作流扩展 P0/P1。

## 已核查依据

- Tencent/LoopForge main，commit `69e4bf093cf26dc72a2b0bc5d7452f86ce96f660`，Local 包版本 0.2.3。
- `local/src/devflow_cli/core.py::materialize_portable`：Codex 项目级 `.agents/skills`，不是 Classic `.codex` 包。
- `local/skills/devflow/adapters/codex/manifest.json`：动态 `spawn_agent`，配合 `send_message`、`wait_agent`。
- `workflow_state.py` 公开 init/prepare/assign/start/finish/approve/resume/validate 接口。
- `prepare --input` 扩展允许输入；原生 `--profile` 只识别内部规则注册表，因此不把工业 Profile 冒充原生 Profile。

## 设计决策

1. `vendor/loopforge` 保存固定版本的必要 Local 源码与许可证，逐文件 SHA-256 校验，不编辑上游文件。
2. `skills/` 为七个规范 Skill；安装器只向本扩展或新建接入工作区复制，不修改用户全局配置。
3. `profiles/` 为三个工业上下文 Profile；`workflows/` 为四条领域阶段定义。领域阶段映射到原生七阶段，不增加第二套流程状态机。
4. `ivw.py` 与 `ivw/` 是薄适配层：校验配置、生成工业上下文、调用上游 CLI。`engines/experiment-engine/` 是实际实验执行系统，管理数据版本、固定 Python runner、配置、模型产物和运行记录；`engines/evaluation-engine/` 是独立评测系统，直接读取预测与独立真值，计算检测、事件、几何与性能指标。两者不是 Prompt，也不取代 LoopForge 状态机。不接 PLC/MES。
5. Supervisor/Executor/Verifier 是专业职责；映射到上游协调者、architect/developer、reviewer/test-engineer。独立性使用真实宿主执行者 ID，而非靠角色文字声明。
6. 十个检查模块按显式请求或领域阶段建议选取；不创建十个常驻 Agent。
7. 数据集、实验、模型、评测和失败案例以内容摘要关联，记录只能追加。只登记本地引用，默认不复制客户数据或模型权重。
8. 现有五个业务项目保持只读。接入工作区的输出写入本项目 `workspaces/`，不得在业务仓库安装技能或生成产物。

## 实施顺序与完成定义

| 优先级 | 工作 | 可观察验收 |
|---|---|---|
| P0 | 固定上游、实现适配安装与完整性检查 | 原生 Portable 安装/status/doctor 可执行，受管文件冲突不覆盖 |
| P0 | 三个 Profile、七个 Skills、四条 Workflow、三个角色 | 名称、引用、阶段映射校验；真实 prepare Prompt 包含领域内容 |
| P0 | Windows 安装、共享、卸载脚本 | 新路径安装可运行；卸载保留用户修改和实验输出 |
| P1 | Experiment Engine 基础版 | 数据集、模型、配置固定；实际运行 Python runner；保留失败和超时；实验与模型可追溯、版本可对比 |
| P2 基础闭环 | Evaluation Engine | 独立读取真值/预测；检测与事件召回、误检漏检、证据绑定、几何误差、性能与切片；不满足门槛失败，不把未评估写成通过 |
| P1 | SOP 与鞍座接入示例 | 只读上下文生成、原生 init/prepare/validate，保护项目状态对照 |
| P1 | 回归测试、Smoke、实现报告 | 标准库测试含失败路径；原生命令集成证据；明确未运行的真实模型和现场验证 |

## 验证边界

本次实现和测试由当前开发会话执行。后续使用 LoopForge 的 medium/large 流程时保留其 REQUIREMENT 用户确认与独立阶段执行门禁，不自动批准。结构/脚本 Smoke 不能声称完成真实多 Agent 协作、模型训练、客户数据评测或生产验收。

## 架构修订依据

用户 2026-11-17 明确纠正：四大核心组件为 Vision Profiles、Vision Skills、Experiment Engine、Evaluation Engine；Vision Workflows 将四者与 LoopForge 组合，Project Layer 连接现有项目。后续必须保持这一方向。P0 为集成与专业上下文，P1 为工作流和实际实验，P2 为独立评测，P3 为真实 SOP/点云专项闭环，P4 为 OCR/分割等扩展。此次为避免引擎沦为长期规划，实际建设 P1 runner 和 P2 的基础确定性评测；不宣称 P2 全量或 P3 已完成。OCR/分割保留为后续范围，不创建假可用 Profile。

## 来源

- https://github.com/Tencent/LoopForge/tree/69e4bf093cf26dc72a2b0bc5d7452f86ce96f660/local
- https://github.com/Tencent/LoopForge/blob/69e4bf093cf26dc72a2b0bc5d7452f86ce96f660/local/skills/README.md
- https://learn.chatgpt.com/docs/build-skills

## 本轮交付状态（2026-11-17）

P0/P1 交付及基础确定性评测闭环已实现并通过验证：51 项标准库测试、56 次子命令 Smoke、Portable status/doctor、共享包解压搬迁后的实验与评测。完整证据、修复清单和 8 组合成实验结果见 [实现报告](implementation-report.md)。

该结果只覆盖合成基础闭环；真实模型/客户数据/现场验证、独立多 Agent 审查及 P2 全量/P3 仍未完成。REQUIREMENT 确认门禁保留，未代批。
