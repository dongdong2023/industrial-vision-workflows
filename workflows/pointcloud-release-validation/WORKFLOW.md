# pointcloud-release-validation

Profile：pointcloud-3d。具体阶段定义以 workflow.json 为准。

1. REQUIREMENT / Supervisor：固定待发布代码、配置、模型、数据与验收协议。
2. DESIGN / Executor：设计回归、困难反例、协议、超时、回退与现场待验矩阵。
3. IMPLEMENT / Executor：Experiment Engine 在隔离输出目录运行冻结候选，禁止修改被验证阈值。
4. REVIEW / Verifier：检查实际 diff、原限值、默认关闭开关与版本追溯。
5. TEST / Verifier：Evaluation Engine 对比同版本真值，检查误检漏检、几何误差、尾时延与失败率。
6. KNOWLEDGE / Executor：按需记录新边界和恢复方法。
7. SUMMARY / Supervisor：形成离线验收候选；现场资格与发布审批另行决定。
