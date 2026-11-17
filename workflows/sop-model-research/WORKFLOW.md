# sop-model-research

Profile：sop-research。具体阶段定义以 workflow.json 为准。

1. REQUIREMENT / Supervisor：冻结动作语义、可见证据和独立录像切分；未知完成状态不作负例。
2. DESIGN / Executor：选择检测/跟踪/姿态/时序候选，固定预算、基线、许可证与实验配置。
3. IMPLEMENT / Executor：Experiment Engine 运行固定 runner；记录实际模型、配置、预测与失败。
4. REVIEW / Verifier：检查泄漏、事件语义、时间因果和证据绑定；独立审查实际变更。
5. TEST / Verifier：Evaluation Engine 计算 Event Recall、误事件、Evidence Binding 和实时性，分工位/遮挡切片。
6. KNOWLEDGE / Executor：按需沉淀可复用失败模式和被否定假设。
7. SUMMARY / Supervisor：汇总证据和未评估项，给出下一步研究决策。
