---
name: vision-edge-deployment
description: 在评估视觉模型边缘部署、实时性、稳定性和回退条件时使用。
---

# vision-edge-deployment

冻结目标硬件、runtime、模型精度、预处理和配置；分别记录启动、预热、稳态与长时间运行。核对丢帧、失败调用、P95、断流重连和资源峰值。基础引擎只校验采集的 trace，尚未采集的 GPU/内存/温度不能写已通过；不得自动安装服务、接 PLC/MES 或变更生产开关。

从本扩展根目录运行下列入口；安装到接入工作区时，通过 `.ivw/install.json` 的 `extension_root` 定位根目录，所有路径加引号。不要依赖调用者当前目录猜测数据路径。

```powershell
python ivw.py evaluate --help
```

产物类型：`edge-validation`。字段和实例见 [references/contract.md](references/contract.md)。需要的 Profile、阶段和检查模块由 `ivw.py prepare` 注入；不额外创建常驻 Agent。
