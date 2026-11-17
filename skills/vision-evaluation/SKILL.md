---
name: vision-evaluation
description: 在独立验证视觉实验效果、泛化、几何误差或验收门槛时使用。
---

# vision-evaluation

从固定数据版本获取真值并直接计算指标，不信任 runner 自报成绩。报告漏检、误检、事件召回、证据绑定、位置误差、切片和未评估项。比较同一数据/协议的基线与候选；UNKNOWN、缺失预测、无负例和样本不足不得隐藏。评测 PASS 只针对约定离线指标，不是生产授权。

从本扩展根目录运行下列入口；安装到接入工作区时，通过 `.ivw/install.json` 的 `extension_root` 定位根目录，所有路径加引号。不要依赖调用者当前目录猜测数据路径。

```powershell
python ivw.py evaluate --help
```

产物类型：`evaluation-report`。字段和实例见 [references/contract.md](references/contract.md)。需要的 Profile、阶段和检查模块由 `ivw.py prepare` 注入；不额外创建常驻 Agent。
