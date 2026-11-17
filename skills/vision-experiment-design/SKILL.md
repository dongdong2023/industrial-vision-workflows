---
name: vision-experiment-design
description: 在设计、运行和对比可追溯视觉实验或训练适配器时使用。
---

# vision-experiment-design

冻结数据版本、runner 哈希、模型/代码版本、参数、种子、资源与停止条件。一次改变一个主要因素。用 Experiment Engine 的登记和 run 接口实际执行，失败与超时也要保留；不要让候选 runner 读取真值评分。训练可使用受信任的本地 Python runner，产物写到指定输出目录。

从本扩展根目录运行下列入口；安装到接入工作区时，通过 `.ivw/install.json` 的 `extension_root` 定位根目录，所有路径加引号。不要依赖调用者当前目录猜测数据路径。

```powershell
python ivw.py experiment run --config examples/experiments/sop-baseline.json --store local/experiments
```

产物类型：`experiment-record`。字段和实例见 [references/contract.md](references/contract.md)。需要的 Profile、阶段和检查模块由 `ivw.py prepare` 注入；不额外创建常驻 Agent。
