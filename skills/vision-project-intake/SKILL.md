---
name: vision-project-intake
description: 在接入视觉项目、澄清问题与冻结验收范围时使用。
---

# vision-project-intake

读取项目指令、当前进展、工作树和唯一结果权限链。用可观察行为描述问题，区分客户事实、助手推断和未知。选择专业 Profile 与 Workflow。固定只读源路径、输出路径、数据权限和阈值；不得把只读接入升级为业务修改。

从本扩展根目录运行下列入口；安装到接入工作区时，通过 `.ivw/install.json` 的 `extension_root` 定位根目录，所有路径加引号。不要依赖调用者当前目录猜测数据路径。

```powershell
python ivw.py context --example sop --out workspaces/sop-context.md
```

产物类型：`project-intake`。字段和实例见 [references/contract.md](references/contract.md)。需要的 Profile、阶段和检查模块由 `ivw.py prepare` 注入；不额外创建常驻 Agent。
