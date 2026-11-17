import argparse
import json
import subprocess
import sys
from pathlib import Path

from .common import ROOT, child, guard_workspace, read_json, runtime_env
from . import integration


def validate():
    result = integration.verify_vendor()
    skills = read_json(ROOT / "skills/manifest.json")["skills"]
    profiles = list((ROOT / "profiles").glob("*/profile.json"))
    workflows = list((ROOT / "workflows").glob("*/workflow.json"))
    checks = read_json(ROOT / "checks/manifest.json")["checks"]
    upstream_route = read_json(integration.VENDOR / "local/skills/devflow/config/workflow.json")["routes"]["medium"]
    if (len(skills), len(profiles), len(workflows), len(checks)) != (7, 3, 4, 10):
        raise ValueError("首批组件数量与交付约定不一致")
    if len(set(skills)) != len(skills):
        raise ValueError("Skill 标识符重复")
    for path in profiles:
        profile = read_json(path)
        if profile["id"] != path.parent.name or not profile.get("rules"):
            raise ValueError("Profile 标识符或规则无效")
        if not (path.parent / "PROFILE.md").is_file():
            raise ValueError("Profile 缺少说明")
    for spec in checks.values():
        if not child(ROOT / "checks", spec["file"]).is_file():
            raise ValueError("检查模块文件缺失")
    for name in skills:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        if not text.startswith(f"---\nname: {name}\ndescription: ") or "{{" in text:
            raise ValueError(f"Skill 元数据或模板无效: {name}")
        if not (ROOT / "skills" / name / "references/contract.md").is_file():
            raise ValueError(f"Skill 缺少引用契约: {name}")
    roles = read_json(ROOT / "agents/roles.json")
    if set(roles) != {"Supervisor", "Executor", "Verifier"}:
        raise ValueError("专业职责必须为三个约定角色")
    for name in roles:
        if not (ROOT / "agents" / (name.lower() + ".md")).is_file():
            raise ValueError("角色说明缺失")
    for path in workflows:
        workflow = read_json(path)
        if workflow["id"] != path.parent.name:
            raise ValueError("Workflow 标识符与路径不一致")
        integration.inspect(workflow["profile"], workflow["id"])
        if workflow["route"] != upstream_route or [s["stage"] for s in workflow["stages"]] != upstream_route:
            raise ValueError("领域阶段必须映射原生路线")
        for stage in workflow["stages"]:
            expected_engine = {"IMPLEMENT": "experiment-engine", "TEST": "evaluation-engine"}.get(stage["stage"])
            if stage["engine"] != expected_engine:
                raise ValueError("实验与评测引擎的阶段映射无效")
            if stage["role"] not in roles or stage["stage"] not in roles[stage["role"]]["stages"]:
                raise ValueError("角色阶段映射无效")
            if set(stage["skills"]) - set(skills):
                raise ValueError("阶段引用未知 Skill")
    for name in ("experiment-engine", "evaluation-engine"):
        if not (ROOT / "engines" / name / "engine.py").is_file():
            raise ValueError("引擎入口缺失")
    for relative in ("README.md", "docs/architecture-and-plan.md", "docs/implementation-report.md", "docs/engine-contracts.md",
                     "scripts/Install.ps1", "scripts/Uninstall.ps1", "scripts/Share.ps1", "scripts/smoke_test.py"):
        if not (ROOT / relative).is_file():
            raise ValueError(f"交付文件缺失: {relative}")
    for relative in read_json(ROOT / "config/share-files.json")["files"]:
        if not child(ROOT, relative).is_file():
            raise ValueError(f"共享清单文件缺失: {relative}")
    return {**result, "profiles": len(profiles), "skills": len(skills), "workflows": len(workflows),
            "checks": len(checks), "roles": len(roles), "engines": 2}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Engines are actual separate processes with their own CLI contracts.
    if argv and argv[0] in {"experiment", "evaluate"}:
        directory = "experiment-engine" if argv[0] == "experiment" else "evaluation-engine"
        return subprocess.run([sys.executable, str(ROOT / "engines" / directory / "engine.py"), *argv[1:]], env=runtime_env()).returncode
    if argv and argv[0] == "state":
        try:
            allowed = {"assign", "start", "finish", "approve", "resume", "validate", "status", "decide-knowledge"}
            if len(argv) < 2 or argv[1] not in allowed or "--state" not in argv:
                raise ValueError("state 需要原生动作与 --state，不允许修改路线或重写状态")
            state = Path(argv[argv.index("--state") + 1]).resolve()
            data = read_json(state)
            project = guard_workspace(data["project_root"])
            if not state.is_relative_to(project / "artifacts") or state.parent != Path(data["artifacts_dir"]).resolve():
                raise ValueError("状态路径与工作区不一致")
            print(integration.command([sys.executable, str(integration.workflow_script(project)), *argv[1:]]), end="")
            return 0
        except (ValueError, OSError, KeyError, IndexError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    parser = argparse.ArgumentParser(description="Industrial Vision Workflows — LoopForge 扩展与双引擎")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    for name in ("install", "uninstall", "status", "doctor"):
        p = sub.add_parser(name)
        p.add_argument("--project", type=Path, default=ROOT)
    p = sub.add_parser("inspect")
    p.add_argument("--profile", required=True)
    p.add_argument("--workflow", required=True)
    p.add_argument("--check", action="append", default=[])
    p.add_argument("--example", choices=("sop", "saddles"))
    p = sub.add_parser("init")
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--workflow", required=True)
    p.add_argument("--check", action="append", default=[])
    p.add_argument("--example", choices=("sop", "saddles"))
    p = sub.add_parser("prepare")
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--request", default="")
    p = sub.add_parser("context")
    p.add_argument("--example", choices=("sop", "saddles"), required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            result = validate()
        elif args.command in {"install", "uninstall"}:
            result = getattr(integration, args.command)(args.project)
        elif args.command == "status":
            result = {"upstream": json.loads(integration.upstream(["skills", "status", "codex", "--project-root", args.project, "--json"]))}
            manifest = args.project / ".ivw/install.json"
            if manifest.exists():
                from .common import child, file_hash
                data = read_json(manifest)
                result["extension_drift"] = [key for key, value in data["files"].items()
                                             if not child(args.project, key).is_file() or file_hash(child(args.project, key)) != value]
        elif args.command == "doctor":
            result = {"upstream": integration.upstream(["doctor", "--project-root", args.project]).strip(), **validate()}
        elif args.command == "inspect":
            result = integration.inspect(args.profile, args.workflow, args.check)
        elif args.command == "init":
            result = integration.init_workflow(args.project, args.slug, args.profile, args.workflow, args.check, args.example)
        elif args.command == "prepare":
            result = integration.prepare(args.state, args.stage, args.request)
        else:
            result = integration.project_context(args.example, args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
