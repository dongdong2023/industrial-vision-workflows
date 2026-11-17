---
name: vision-error-analysis
description: 在检测、动作、拟合、配组或坐标误差需要定位根因时使用。
---

# vision-error-analysis

按最早偏离阶段建立失败案例，保留输入引用、预期、实测和假设。区分数据缺口、观察源、算法规则、坐标变换和产品集成。按需调用 root-cause 与 git-archaeology 检查模块，先构造反证，再用固定基线和候选对照。

从本扩展根目录运行下列入口；安装到接入工作区时，通过 `.ivw/install.json` 的 `extension_root` 定位根目录，所有路径加引号。不要依赖调用者当前目录猜测数据路径。

```powershell
python ivw.py experiment failure --file examples/failure-case.json --store local/experiments
```

产物类型：`failure-case`。字段和实例见 [references/contract.md](references/contract.md)。需要的 Profile、阶段和检查模块由 `ivw.py prepare` 注入；不额外创建常驻 Agent。
