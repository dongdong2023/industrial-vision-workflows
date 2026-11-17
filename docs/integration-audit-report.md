# Industrial Vision Workflows 真实集成审计报告

审计日期：2026-11-17。对象：`916ea02cbb3d90eb74d76d6f7039a05a90303436`，Windows / Python 3.12 / 当前 Codex 宿主。

**总体判定：PARTIAL。真实宿主调度、Portable 原生命令和合成实验评测均有运行证据；完整工业 medium 研发闭环尚未验证，不能判定已完整实现。**

本轮只审计。实现、配置、vendor 和业务项目不作修复；仅新增本报告及本地探针证据，没有批准 REQUIREMENT、提交或 Push。

状态含义：**VERIFIED**＝明确范围内有实际运行证据；**CONFIGURED**＝配置/文档存在，未证明实际运行；**PARTIAL**＝部分成立但仍有缺口；**NOT_VERIFIED**＝没有验证证据；**BLOCKED**＝存在明确前置阻塞。问题被复现的 VERIFIED 不表示相应功能健康。

本地证据根目录：[integration-audit-20261117-1f0efb0f](../local/integration-audit-20261117-1f0efb0f/)。这些日志、探针和合成产物留在本机，不属于已推送提交。主索引为 [audit-index.json](../local/integration-audit-20261117-1f0efb0f/audit-index.json)。

## 1. 总体架构审计

| 架构要素 | 状态 | 实际观察 |
|---|---|---|
| Codex → LoopForge Portable → 工业扩展 | PARTIAL | 宿主真实执行者已绑定原生 small 探针；四条工业 medium 路线只走到 REQUIREMENT |
| LoopForge 是唯一流程状态机 | VERIFIED | 路由、阶段、门禁、执行者和恢复由原生 workflow-state.json 管理；工业 context.json 是上下文快照，run/report 状态是实验记录，没有发现另一套工作流阶段机 |
| 四大核心组件及 Workflow 组合 | VERIFIED | 3 Profiles、7 Skills、双 Engine、4 Workflows 的文件、引用和阶段映射通过校验 |
| 原生阶段与工业实验/评测证据闭环 | PARTIAL | Engine 可实际运行，但原生 finish 不读取 run/evaluation 结论或验证它们属于当前阶段 |

`ivw/cli.py:75` 起分别转发双引擎和原生 state 命令；`ivw/integration.py:138` 起负责领域正文拼接。Portable 按宿主 Prompt 协调，CLI 不直接 spawn Agent 本身不是架构错误；需要核查的是实际协调记录与证据交接。

### 本次标准验证

由独立测试 Agent `/root/audit_test` 实际运行：

| 命令 | 状态 | 结果 |
|---|---|---|
| `python ivw.py validate` | VERIFIED | 退出 0；514 上游文件、3 Profiles、7 Skills、4 Workflows、10 checks、3 roles、2 engines |
| `python -m unittest discover -s tests -v` | VERIFIED | 退出 0；51 tests，45.227 秒，OK |
| `python scripts/smoke_test.py` | VERIFIED | 退出 0；56 条子命令，50.765 秒；安装/卸载/共享/搬迁和合成闭环通过 |

日志和命令时间见 [test/evidence.json](../local/integration-audit-20261117-1f0efb0f/test/evidence.json)。本次 Smoke 为 [smoke-2544d6a198ac44e591496dee859f6501/report.json](../local/smoke-2544d6a198ac44e591496dee859f6501/report.json)。测试通过不代表下文未覆盖能力通过。

## 2. LoopForge Portable 集成

### 上游来源、字节锁定与安装

| 能力 | 状态 | 证据与边界 |
|---|---|---|
| 固定版本与来源 | VERIFIED | 锁声明 Local 0.2.3、commit `69e4bf093cf26dc72a2b0bc5d7452f86ce96f660`；与官方固定提交逐路径核对，没有缺失路径或非换行内容差异 |
| 本地 SHA-256 锁定 | VERIFIED | 514/514 与 upstream.lock.json 一致；这是本地物化快照完整性 |
| 官方原始字节复现 | PARTIAL | 6/514 原始 Git Blob 字节相同；其余 508 个存在 CRLF/LF 差异，转换 CRLF→LF 后 514/514 全部匹配官方 Blob |
| Portable 安装、status、doctor 正常路径 | VERIFIED | 当前项目 portable:codex 受管文件 90 个，changed=0、missing=0；临时新工作区实际安装成功 |
| 项目级工业 Skills 安装 | VERIFIED | `.agents/skills/vision-*` 的 14 个文件安装成功，与 canonical 内容一致 |
| 工业安装异常诊断 | PARTIAL | status 能发现工业 Skill 漂移，doctor 会漏报，见问题 R3 |
| 本轮上游意外变更 | VERIFIED | 审计前后逐文件摘要对照；未编辑 vendor。官方换行差异属于既有物化边界，不是本轮逻辑篡改证据 |

官方来源为 [Tencent/LoopForge 固定提交](https://github.com/Tencent/LoopForge/tree/69e4bf093cf26dc72a2b0bc5d7452f86ce96f660)。本次通过 GitHub API 读取未截断的官方 Git tree，再用 Git Blob 内容摘要比较；并下载关键文件验证 SHA-256。例如 `local/skills/devflow/scripts/workflow_state.py`：官方 `f44855c70c82f9a9bca9bcc894dccfca846b32a462f5e718bd786d5dc6f06362`，本地 `a9cf09c1db15a6c4661a6766d24ec209cbdaed3f9629eaf7366035673ca63902`，仅 1222 行 CRLF 差异。不能把本地锁通过表述为官方原始 SHA-256 全等。

原始核对见 [official-upstream-eol-verification.json](../local/integration-audit-20261117-1f0efb0f/official-upstream-eol-verification.json) 和 [官方关键文件核对](../local/integration-audit-20261117-1f0efb0f/official-upstream-blob-example.json)。vendor 含上游其他宿主/Classic 资产不等于运行时混用；本次实际安装和执行均为 Portable Codex。

### 原生生命周期实测

| 命令/能力 | 状态 | 本次真实成功路径 |
|---|---|---|
| init | VERIFIED | 四个工业 medium/manual/codex 工作流及一个独立原语 small/isolated/codex 探针 |
| prepare | VERIFIED | 四个工业 REQUIREMENT；原语探针 SOLO、SUMMARY；未声称其余工业阶段执行 |
| assign | VERIFIED | SOLO 绑定真实 `/root/audit_executor`，role/type/dispatch_tool 使用原生约定 |
| start | VERIFIED | 工业 REQUIREMENT，以及原语 SOLO、SUMMARY 均实际开始 |
| finish | VERIFIED | Executor 本人完成 SOLO 报告并自检，协调者检查后 finish；SUMMARY 完成，small 状态为 completed；另一 medium REQUIREMENT 完成后等待批准 |
| approve | PARTIAL | 在真正 awaiting_approval=REQUIREMENT 时，不带用户确认的调用被拒绝；状态摘要不变。获用户确认后的成功批准路径未执行 |
| resume | VERIFIED | 分离进程恢复 pending/prepared/in_progress/awaiting_approval/completed，返回相应动作；执行中包含真实 executor ID |
| 工业完整恢复 | PARTIAL | 缺 context.json 时仍能得到原生恢复成功，但工业 prepare 失败；未验证宿主重启后失效 Agent 的重新绑定 |
| validate | VERIFIED | 原生状态和必需报告通过；不等于业务指标或现场验收通过 |

原语 small 探针是单独的只读校验任务，**没有把任何工业 medium 路线降级，也没有绕过 REQUIREMENT**。该探针完成 `prepare → assign → start → 实际执行 → finish → SUMMARY → validate/resume`；四条工业路线仍保持原生路线和确认门禁。恢复测试是 CLI 进程结束后重新读取持久化状态，没有冒充整机崩溃或跨会话 Agent 失效恢复。

[native/evidence.json](../local/integration-audit-20261117-1f0efb0f/native/evidence.json) 与 [native/commands.json](../local/integration-audit-20261117-1f0efb0f/native/commands.json) 记录 52 次命令。探针最初发生 PowerShell stdin 中文编码丢失，已保留原件并用 UTF-8 重做 REQUIREMENT、恢复生成 SOLO Prompt；这属于审计工具过程问题，未归因于项目。

## 3. Codex Agent 调度实测

本环境所需工具**存在并可用**，没有“宿主缺少 Agent 工具”的阻塞。

| 操作 | 状态 | 实际证据 |
|---|---|---|
| 创建独立 Agent | VERIFIED | collaboration.spawn_agent 实际返回下列三个任务 ID；使用独立上下文 |
| 分配给指定 Agent | VERIFIED | 根协调者定向发送任务；原生 assign 原样登记真实 Executor ID；followup_task 定向续派发成功 |
| Agent 间消息 | VERIFIED | Executor 向 Reviewer 发送 `IVW-AUDIT-1F0E`，Reviewer 用真实 send_message 回复 ACK |
| 等待完成 | VERIFIED | wait_agent 实际返回 `Wait completed.`、timed_out=false；Executor 回复 `WAIT-ACK-1F0E` |
| 获得真实 executor ID | VERIFIED | 使用宿主返回的 canonical task ID，不是自拟 UUID；原生 SOLO 状态保存相同 ID |
| 对已有提交的独立 Review/Test | VERIFIED | Reviewer 独立审查当前实现；Tester 独立运行三项验证，均不同于 Executor 和原开发协调者 |
| 原生 IMPLEMENT→REVIEW→TEST 的阶段独立性 | NOT_VERIFIED | 本次未越过需求确认，不能将审计角色独立升级成原生阶段串行完成 |
| 原生 assign 对宿主身份的认证 | PARTIAL | 原生代码检查角色、类型、ID 非协调者/不跨阶段复用；不会查询宿主确认 ID 存在或报告作者，仍需真实工具回执 |

真实 ID：协调者 `/root`；执行审计 `/root/audit_executor`；独立审查 `/root/audit_review`；独立测试 `/root/audit_test`。共享文件系统不是权限隔离沙箱。

[host-agent-evidence.json](../local/integration-audit-20261117-1f0efb0f/host-agent-evidence.json) 记录宿主回执摘要；双方消息原文见 [executor/evidence.json](../local/integration-audit-20261117-1f0efb0f/executor/evidence.json) 与 [review/evidence.json](../local/integration-audit-20261117-1f0efb0f/review/evidence.json)。本次没有用任何 mocked executor 测试字符串作为真实调度证据。

## 4. Vision Profiles 和 Vision Skills

### Profiles

| Profile | 状态 | 实际验证 |
|---|---|---|
| sop-research | VERIFIED | sop-model-research 的真实 REQUIREMENT Prompt 包含全部 JSON 规则和对应 Skill 正文 |
| sop-product | VERIFIED | sop-product-development 同上，含产品交付、异常/断流等专业要求 |
| pointcloud-3d | VERIFIED | 两条点云路线同上，含单位、坐标、单体/配组、空位判断及默认关闭授权要求 |

“规则进入 Prompt”不代表规则描述的工业能力已实现。后续阶段的规则注入仍为 CONFIGURED，未实际进入原生执行。

### Skills

当前根目录宿主技能目录确实暴露全部七项；独立 Executor 实际读取 `.agents/skills` 的 7 个 SKILL.md 和 7 个 contract，摘要与 canonical 一致。**当前会话发现/加载：VERIFIED。**

| Skill | 本次应用状态 | 应用证据及限制 |
|---|---|---|
| vision-project-intake | VERIFIED | inspect、只读项目上下文及审计范围记录；不是生产需求验收 |
| vision-dataset-audit | VERIFIED | 合成 manifest 实际登记及分组/泄漏测试；不验证标签真实性或现场代表性 |
| vision-model-selection | PARTIAL | 按指令比较合成候选/配置并形成选择记录；未比较真实工业模型 |
| vision-experiment-design | VERIFIED | 固定配置、两个已审阅本地 runner 注册、四个真实进程和模型产物 |
| vision-error-analysis | VERIFIED | 定位 SOP 错误样本引用、分析绑定退化并实际追加失败记录 |
| vision-evaluation | VERIFIED | 实际独立评测及 baseline/candidate 比较，错误绑定候选 FAIL |
| vision-edge-deployment | PARTIAL | 读取技能并解释 trace/部署边界，形成核验清单；没有边缘设备部署或长稳测试 |

Codex 在此通过读取 Skill 指令并执行相应任务应用 Skill，没有另一个可供核验的专用 invoke 回执。**新安装临时工作区重开 Codex 后的发现/激活：NOT_VERIFIED**，不能从文件复制或 Prompt 内联推导热加载成功。内联后的相对 `references/contract.md` 及后续 Engine 证据输入交接也尚未通过真实后续阶段验证。

详见 [executor/findings.md](../local/integration-audit-20261117-1f0efb0f/executor/findings.md)。

## 5. 四条 Vision Workflow 验证

| Workflow | Profile | REQUIREMENT | 后续六阶段 |
|---|---|---|---|
| sop-model-research | sop-research | VERIFIED：真实生成 Prompt，逐条核对正文；另完成需求报告进入待确认 | CONFIGURED；实际继续执行 BLOCKED |
| sop-product-development | sop-product | VERIFIED：真实生成 Prompt，逐条核对正文 | CONFIGURED；实际继续执行 BLOCKED |
| pointcloud-error-diagnosis | pointcloud-3d | VERIFIED：真实生成 Prompt，逐条核对正文 | CONFIGURED；实际继续执行 BLOCKED |
| pointcloud-release-validation | pointcloud-3d | VERIFIED：真实生成 Prompt，逐条核对正文 | CONFIGURED；实际继续执行 BLOCKED |

四条路线目前采用相同的角色/Skill/Engine 组合，专业差异来自 Profile 和阶段 goal：

| 阶段 | 角色 | Skill | Engine | 阶段实测状态 |
|---|---|---|---|---|
| REQUIREMENT | Supervisor | project-intake、dataset-audit | 无 | VERIFIED |
| DESIGN | Executor | model-selection、experiment-design | 无 | CONFIGURED |
| IMPLEMENT | Executor | experiment-design、error-analysis | experiment-engine | CONFIGURED |
| REVIEW | Verifier | evaluation | 无 | CONFIGURED |
| TEST | Verifier | evaluation、edge-deployment | evaluation-engine | CONFIGURED |
| KNOWLEDGE | Executor | error-analysis | 无 | CONFIGURED；原生条件阶段 |
| SUMMARY | Supervisor | evaluation | 无 | CONFIGURED |

上表 Skill 均省略 `vision-` 前缀。独立审查另对 28 项组合做正文格式化检查，但其中后续 24 项**只作 formatter 预览，原生转换被 mock**；其结果只支持 CONFIGURED，不支持阶段执行 VERIFIED。

引擎名注入不等于自动执行；宿主仍需实际调用 Engine、引用结果并按原生门禁 finish。当前工业 context 被加入原生 `--input`，但数据、协议、run/report 和各 Skill 引用契约尚未形成经实测的后续阶段输入包。原生输入清单也不是操作系统访问沙箱。

## 6. Experiment Engine 验证

| 能力 | 状态 | 证据 |
|---|---|---|
| 数据集登记、内容版本、分组泄漏拒绝 | VERIFIED | 本次真实登记及标准测试的 group/content 跨 split 拒绝 |
| Runner 注册、固定文件摘要 | VERIFIED | Executor 完整阅读示例后，复制至审计目录并注册两个本地合成 runner；变更后拒绝的测试通过 |
| 真实 Python 进程与隔离工作目录 | VERIFIED | Executor 四个实际进程退出 0，Smoke 八组实际 run；有命令、stdout/stderr、wall time、产物摘要 |
| 训练/推理及模型版本记录 | VERIFIED | 合成标定使用 4 个 train 组，输出模型；两份模型登记记录绑定 run/dataset/config/hash |
| 失败、超时、历史追溯 | VERIFIED | 本次标准测试实际触发失败/超时并保留记录，run 唯一追加，篡改输入/配置/预测被拒绝 |
| 预测输出完整协议校验 | PARTIAL | `samples:[null]` 仍可被实验标记 completed，见 R2 |
| 真实工业视觉模型 Runner | NOT_VERIFIED | 内置只有 synthetic-observer 和 synthetic-trainer；本次没有运行客户模型 |
| 原生任务/阶段/执行者追溯 | PARTIAL | 实验内部可追溯，但记录没有 workflow/state/stage/executor 的原生关联，见 R1 |

合成标定是真实计算进程，但不是点云网络训练；observer 只是按观测 score 过滤。版本字符串/code_version 是调用者声明，依赖和硬件环境没有因此被冻结。held-out 真值未直接进入 runner input，但受信任 Python 能访问本机，不能称安全隔离。

## 7. Evaluation Engine 验证

| 能力 | 状态 | 实际观察 |
|---|---|---|
| 独立读取 Ground Truth 与固定预测 | VERIFIED | 校验数据版本、run/产物摘要后独立计算；没有使用 runner 自报总分 |
| Precision、Recall、TP/FP/FN、切片 | VERIFIED | 本次标准测试、Smoke 和 Executor 实验有确定性结果；重复预测不会重复计 TP |
| 事件召回与 Evidence Binding | VERIFIED | SOP candidate recall=1.0，但 binding=0.8，独立评测退出 1/FAIL |
| 点云几何误差 | VERIFIED | 合成标定最大中心误差约 0.12 m→8.88e-16 m，baseline FAIL、candidate PASS |
| 缺失/不完整评测数据识别 | VERIFIED | 缺预测（含负例）、无负例、样本不足、错误版本、非法协议被拒绝或 FAIL；缺 trace 为 null 并导致必需指标失败 |
| Baseline/Candidate 比较 | VERIFIED | 实际比较同数据/协议报告，不同协议/版本比较拒绝测试通过 |
| 拒绝不达标候选的评测结论 | VERIFIED | 证据绑定退化被明确 FAIL；不自动晋级模型 |
| 把 FAIL 绑定为原生 TEST/交付阻断 | PARTIAL | 当前依赖宿主解释退出码、引用结果，finish 没有机器可检查的工业证据约束 |
| 配组/尺寸、真实物理完成、现场性能 | NOT_VERIFIED | 当前只测匹配中心、引用/时间字段与 runner trace，不具备这些结论的证据 |

对抗自报分数的现有测试确实让 runner 写 precision=recall=1 并清空预测；独立评测仍得到 recall=0、precision=null。本次所有效果证据均为 **synthetic**；真实客户数据离线效果和现场能力都为 **NOT_VERIFIED**。评测可选择 train split，因此“独立计算”本身也不能证明 held-out 泛化。

## 8. 已发现的问题

| 编号 | 状态/优先级 | 问题与影响 | 证据 |
|---|---|---|---|
| R1 | PARTIAL / P1 | state→run→eval 未成为阶段完成契约，不能确定某次 TEST 验证了当前 IMPLEMENT、冻结协议与独立执行者；这是集成缺口，不是已复现的错误 TEST finish | cli.py:75–88；integration.py:138；Engine 记录；review/probe-results.json |
| R2 | VERIFIED / P2 | 正常退出但输出 `samples:[null]` 的受审计 runner 被 Experiment 标 completed/exit 0；Evaluation 随后正确拒绝/exit 2，原记录仍 completed | experiment-engine/engine.py:68–71；review/probe-results.json |
| R3 | VERIFIED / P2 | 自建工作区工业 Skill 被改后，status 列漂移而 doctor 仍 healthy/exit 0；临时文件已恢复 | cli.py:125–133；review/health-probe-results.json |
| R4 | VERIFIED / P2 | 工业 context.json 缺失时，native resume/validate 成功，但工业 prepare 失败；缺失上下文的恢复诊断不完整 | integration.py:144；review/followup-probe-results.json |
| T1 | VERIFIED / P1 | 原有门禁测试只触发 next-stage/not-awaiting 检查，未到用户确认分支；本次额外探针验证不等于已纳入自动回归 | tests/test_integration.py:76–79；Smoke stderr；test/findings.md |
| T2 | VERIFIED / P1 | 原有套件没有 assign/finish/resume 成功链或真实 Agent 调度覆盖；Prompt 主要断言名称，不逐条断言正文 | tests/test_integration.py:60–84；scripts/smoke_test.py:64–76 |
| U1 | VERIFIED / P2 | 本地锁与官方原始字节存在既有 EOL 差异；来源内容可核对，但缺少对物化转换与官方摘要的明确双层记录 | official-upstream-eol-verification.json |

另外两个边界：原生 TEST 内容验证器接受一份明确写 FAIL 的格式完整报告（只证明格式检查，不代表真实 TEST finish 误通过）；被门禁拒绝的 prepare 仍先写出 DESIGN-context.md，但没有生成完整 Prompt 或改变状态。均未据此推断正常宿主必然误放行。

独立审查的复现步骤、命令和行号见 [review/findings.md](../local/integration-audit-20261117-1f0efb0f/review/findings.md)。本轮未修复任何上述问题。

## 9. 缺失能力与阻塞原因

| 项目 | 状态 | 原因 |
|---|---|---|
| Codex spawn/send/wait 工具 | VERIFIED | 当前环境齐备，实际调用成功，不构成阻塞 |
| 四条工业路线的 DESIGN 及后续真实阶段 | BLOCKED | REQUIREMENT 尚未获用户明确确认；本任务明确禁止自动批准 |
| 完整 medium IMPLEMENT/REVIEW/TEST 独立执行与汇总 | NOT_VERIFIED | 本次审计角色与 small 探针不能代替该运行证据 |
| 宿主重启/Agent ID 失效后的工业恢复 | NOT_VERIFIED | 只验证持久化状态的跨 CLI 进程读取；存在工业 context 检查缺口 |
| 新目标工作区新 Codex 会话的 Skills 发现 | NOT_VERIFIED | 未重新打开目标工作区会话；仅当前根目录会话已实测 |
| 真正模型、客户离线数据、边缘设备与现场 | NOT_VERIFIED | 本轮只获准运行经审阅的合成示例；没有相应数据/设备/模型运行证据 |

只读核验比较受跟踪文件内容、HEAD，以及保护快照所覆盖的三个 Git 项目 HEAD/status/diff 和五份文档摘要。非 Git 项目与所有未跟踪文件不是完整树内容审计，不能扩大解释“状态未变”的含义。

## 10. 下一阶段 P0/P1/P2 计划（仅建议，未实施）

| 优先级 | 建议动作 | 可观察验收 |
|---|---|---|
| P0 | 在薄适配层补原生阶段到 run/evaluation 的证据契约，不增加第二状态机；保留来源、数据/协议摘要、实际 executor 与失败结果的对应 | 当前 IMPLEMENT 与 TEST 可追溯，缺报告、错误协议或 FAIL 不会被宣告验收通过；格式验证与业务通过明确区分 |
| P0 | 用户确认一个具体 REQUIREMENT 后，再进行真实 medium 全链路验收；独立 DESIGN/IMPLEMENT/REVIEW/TEST 按原生顺序派发 | 真实工具回执、不同阶段 ID、原生产物、输入包、实际引擎结果、拒绝路径、恢复和最终 SUMMARY 全部可追溯；不得代批需求 |
| P1 | 修复 doctor 工业漂移、context 缺失恢复诊断、非法预测 completed 状态；补 T1/T2 的实际分支断言和内容断言 | 漂移/缺失/非法输出给出准确状态；确认门禁分支和生命周期回归测试真实触达 |
| P1 | 明确官方原始摘要与本地物化摘要/EOL 策略；整理内联 Skill 契约与引擎证据的输入路径 | 干净检出可复现；不把本地锁当官方原始字节；真实后续阶段可读到冻结的必要证据 |
| P1 | 验证新工作区 Codex 发现七项 Skill、冷恢复与失效执行者处理 | 新会话发现/实际应用有回执或运行证据，中断后不盲信过期 ID |
| P2 | 经用户另行确认后接入一个受审阅的真实工业模型 runner，使用独立真值及分组留出数据 | 模拟、离线、现场分级报告；模型、依赖、数据版本及误差分析可追溯 |
| P2 | 扩展 SOP 产品异常/恢复、点云配组/尺寸及独立硬件性能验证 | 按领域验收协议新增实际负例、缺失/未知处理和设备运行证据，不用合成成绩替代 |

## 最终结论

**对“已经完整实现 Codex + LoopForge + Industrial Vision Workflows 研发闭环”的验收主张，本次不能给出通过结论；当前为 PARTIAL。**

已经证明的是真实宿主可调度、原生状态机可运行、领域上下文实际注入，以及合成实验→独立评测→比较→失败留档的工具级链路。尚未证明四条工业路线中经过用户确认的完整七阶段研发闭环，原生阶段与工业结果之间也还有明确证据契约缺口。不能因配置齐全、51 项测试或一次 small 探针通过就宣称完整打通。

审计到此结束，等待用户确认下一步；未实施修复、自动批准、提交或 Push。
