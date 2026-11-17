# Codex Portable 适配

`python ivw.py install --project <新工作区>` 调用固定源码的原生 `loopforge skills install codex`，再把七个专业 Skill 复制到项目 `.agents/skills/`。不写用户全局目录，不使用 Classic `.codex` 包。安装状态分属 `.devflow/install-state.json` 与 `.ivw/install.json`。

Profile 不是 Codex CLI 的模型配置 profile，也不是上游内置规则的 `--profile`。本扩展通过 `ivw.py init --profile ... --workflow ...` 选择工业配置，`ivw.py prepare` 在原生 `prepare --emit-prompt --input` 基础上附加领域正文。生成的 `industrial/<STAGE>-prompt.md` 是完整派发输入。

1. 协调者读取工作区指令，在 REQUIREMENT 当前会话调用 `$devflow-clarify-requirements`，生成并校验原生报告。
2. 用户明确确认需求后才运行原生 `approve --stage REQUIREMENT --user-confirmed`；本扩展不代批。
3. DESIGN、IMPLEMENT、REVIEW、TEST 每阶段以完整 Prompt 创建全新独立 Agent，真实 `spawn_agent` 返回 ID 后再 `assign --executor-type dynamic --dispatch-tool spawn_agent`、`start`。
4. 原生角色 ID 以 vendor 中 `agents/manifest.json` 为准，不把 Supervisor/Executor/Verifier 名称写进上游 assign 的 role 参数。专业角色映射见 `agents/roles.json`。
5. 执行者填写原生 Markdown 产物；Experiment 与 Evaluation 结果作为引用证据，不能代替上游必需报告。
6. 运行原生 `finish`、manual 门禁与 `resume/validate`。KNOWLEDGE 按需执行或记录理由跳过，SUMMARY 由协调者汇总。

单 Skill 可直接输入 `$vision-dataset-audit` 等名称；完整工业流程用下述请求：

```text
请使用 $devflow 和 $vision-project-intake，在当前独立接入工作区运行 pointcloud-error-diagnosis，加载 pointcloud-3d。源项目只读，按 ivw.py prepare 生成的完整 Prompt 派发阶段；实际实验使用 Experiment Engine，验收由独立 Verifier 调用 Evaluation Engine。
```

宿主缺少 spawn_agent/send_message/wait_agent 时必须报告能力缺口，不能用虚构 ID 假装独立；按上游规则获得明确授权后才能降级。本次确定性 Smoke 不创建假 Agent、不批准需求、不宣称完整多 Agent 已验证。

来源：固定版本的 `local/src/devflow_cli/core.py`、`local/skills/devflow/adapters/codex/`。上游 README 中残留的全局技能安装文字与实际安装器不同，本扩展以已执行的安装器行为为准。
