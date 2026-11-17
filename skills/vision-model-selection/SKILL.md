---
name: vision-model-selection
description: 在比较检测、姿态、视频时序或几何方法并选择实验候选时使用。
---

# vision-model-selection

按可观察信号、数据量、许可证、硬件与时延预算列出基线和候选。引用一手资料；厂商成绩、论文成绩、本地复现与现场结果分开。每个候选给出淘汰条件和增量价值，不把模型建议提升为业务结果。

从本扩展根目录运行下列入口；安装到接入工作区时，通过 `.ivw/install.json` 的 `extension_root` 定位根目录，所有路径加引号。不要依赖调用者当前目录猜测数据路径。

```powershell
python ivw.py inspect --profile sop-research --workflow sop-model-research
```

产物类型：`model-selection`。字段和实例见 [references/contract.md](references/contract.md)。需要的 Profile、阶段和检查模块由 `ivw.py prepare` 注入；不额外创建常驻 Agent。
