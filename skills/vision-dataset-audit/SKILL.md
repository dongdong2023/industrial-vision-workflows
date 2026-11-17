---
name: vision-dataset-audit
description: 在视频、点云数据登记或检查样本质量、分组泄漏、版本变化时使用。
---

# vision-dataset-audit

核对单位、坐标/帧时间、标签语义、来源与授权。按车辆/录像/周期的 group 划分 split，重复内容跨集合立即拒绝。保存完整性哈希与缺失项。工具只做结构与泄漏检查，标签准确性和现场代表性仍需独立复核。

从本扩展根目录运行下列入口；安装到接入工作区时，通过 `.ivw/install.json` 的 `extension_root` 定位根目录，所有路径加引号。不要依赖调用者当前目录猜测数据路径。

```powershell
python ivw.py experiment dataset --file examples/datasets/sop.json --store local/experiments
```

产物类型：`dataset-audit`。字段和实例见 [references/contract.md](references/contract.md)。需要的 Profile、阶段和检查模块由 `ivw.py prepare` 注入；不额外创建常驻 Agent。
