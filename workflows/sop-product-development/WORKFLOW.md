# sop-product-development

Profile：sop-product。具体阶段定义以 workflow.json 为准。

1. REQUIREMENT / Supervisor：冻结工艺语义、唯一终态链与异常行为。
2. DESIGN / Executor：设计观察到 FSM 到 Gateway 的接口、失效处理与回退。
3. IMPLEMENT / Executor：在授权工作区实现并运行回放/模型 runner，业务源项目保持只读。
4. REVIEW / Verifier：审查对象身份、过期、幂等和异常路径。
5. TEST / Verifier：独立评测事件/证据和性能，测试断流、重连、异常与版本回退。
6. KNOWLEDGE / Executor：记录新增约束和调试依据。
7. SUMMARY / Supervisor：交付候选与限制；不自动激活生产。
