# pointcloud-error-diagnosis

Profile：pointcloud-3d。具体阶段定义以 workflow.json 为准。

1. REQUIREMENT / Supervisor：明确漏检/误检/配组/位置误差，固定数据、单位和坐标。
2. DESIGN / Executor：建立最早偏离阶段的根因假设和单变量对照。
3. IMPLEMENT / Executor：Experiment Engine 运行基线与候选几何 runner，保留全部被拒案例。
4. REVIEW / Verifier：审查是否放宽限制、使用目标数量或旧证书替代当前支持。
5. TEST / Verifier：Evaluation Engine 独立计算 TP/FP/FN、配组/定位误差与车辆切片。
6. KNOWLEDGE / Executor：保留反证、失败案例与坐标约束。
7. SUMMARY / Supervisor：交付根因、方案、实际改善和不确定性，不发装载指令。
