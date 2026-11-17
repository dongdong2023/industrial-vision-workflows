# experiment-record 产物约定

记录 scope、数据版本、代码/模型/配置摘要、实际命令、观察结果、限制与证据路径。
结构化实例位于扩展根目录 examples/；完整工具契约见 docs/engine-contracts.md。
实验与评测通过 dataset_id、run_id、config_hash、预测哈希关联，历史失败不得覆写。
不把模拟数据成绩、历史报告或同一场景反复调参称作现场资格。
