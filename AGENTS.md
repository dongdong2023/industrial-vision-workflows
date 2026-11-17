# Industrial Vision Workflows

用户可见内容使用简体中文。先读 README.md、docs/architecture-and-plan.md 和 docs/implementation-report.md。
四大组件是 Profiles、Skills、Experiment Engine、Evaluation Engine；Workflow 组合四者与 LoopForge。
LoopForge Portable 是唯一流程状态机；不编辑 vendor/，不混用 Classic，不自动批准 REQUIREMENT。
现有项目只读，具体根目录见 config/protection.json；不得切分支、stash、提交或 Push 这些项目。
本项目未经用户明确批准也不得 Push。原始客户数据和权重只允许本地引用，禁止放进共享包。
Experiment runner 是受信任的本地 Python 程序，工作目录隔离不是安全沙箱；不得写入只读项目。
Evaluation 从独立真值计算指标，不能照抄 runner 自报分数。模拟、离线、现场证据等级分别报告。
标准验证：python -m unittest discover -s tests -v；python scripts/smoke_test.py；python ivw.py validate。
只创建完成任务需要的 Agent；未实际独立执行的审查不得写成独立审查通过。
