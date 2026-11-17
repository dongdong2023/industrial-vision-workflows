"""Invoke the pinned Portable CLI, preserving upstream ownership of state."""
import json
import subprocess
import sys
from pathlib import Path

from .common import ROOT, child, file_hash, guard_workspace, guard_write, read_json, runtime_env, save_json, stamp

VENDOR = ROOT / "vendor/loopforge"


def verify_vendor():
    lock = read_json(ROOT / "upstream.lock.json")
    for name, expected in lock["files"].items():
        path = child(VENDOR, name)
        if not path.is_file() or file_hash(path) != expected:
            raise ValueError(f"上游文件缺失或被修改: {name}")
    extras = {p.relative_to(VENDOR).as_posix() for p in VENDOR.rglob("*")
              if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}}
    if extras != set(lock["files"]):
        raise ValueError("上游快照存在未登记文件")
    return {"commit": lock["commit"], "files_verified": len(lock["files"])}


def upstream(args):
    verify_vendor()
    env = runtime_env()
    env["PYTHONPATH"] = str(VENDOR / "local/src")
    env["DEVFLOW_ASSET_ROOT"] = str(VENDOR / "local")
    return command([sys.executable, "-m", "devflow_cli.cli", *map(str, args)], env)


def command(args, env=None):
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env or runtime_env())
    if result.returncode:
        raise ValueError(f"命令失败 ({result.returncode}): {result.stdout}\n{result.stderr}")
    return result.stdout


def install(project):
    project = guard_workspace(project)
    manifest_path = project / ".ivw/install.json"
    previous = read_json(manifest_path) if manifest_path.exists() else {"files": {}}
    payload = {}
    for name in read_json(ROOT / "skills/manifest.json")["skills"]:
        for source in (ROOT / "skills" / name).rglob("*"):
            if source.is_file():
                key = ".agents/skills/" + source.relative_to(ROOT / "skills").as_posix()
                payload[key] = source
    # Preflight before upstream mutation. User edits are never silently overwritten.
    for key, source in payload.items():
        target = child(project, key)
        guard_write(target)
        if target.exists() and (key not in previous["files"] or file_hash(target) != previous["files"][key]):
            raise ValueError(f"未托管或被修改的 Skill 冲突: {target}")
    project.mkdir(parents=True, exist_ok=True)
    output = upstream(["skills", "install", "codex", "--project-root", project])
    for key, source in payload.items():
        target = child(project, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    save_json(manifest_path, {"version": 1, "extension_root": str(ROOT), "installed_at": stamp(),
                           "files": {k: file_hash(v) for k, v in payload.items()}})
    return {"project": str(project), "extension_files": len(payload), "upstream": output.strip()}


def uninstall(project):
    project = guard_workspace(project)
    manifest = project / ".ivw/install.json"
    removed, preserved = [], []
    if manifest.exists():
        data = read_json(manifest)
        # Resolve every destination before doing any deletion.
        targets = [(key, guard_write(child(project, key)), expected) for key, expected in data["files"].items()]
        if any(not key.startswith(".agents/skills/vision-") for key, _, _ in targets):
            raise ValueError("安装清单包含非本扩展路径")
        for key, target, expected in targets:
            if target.exists():
                if file_hash(target) == expected:
                    target.unlink()
                    removed.append(key)
                else:
                    preserved.append(key)
        if preserved:
            save_json(manifest, {**data, "files": {k: data["files"][k] for k in preserved}})
        else:
            manifest.unlink()
    result = upstream(["skills", "uninstall", "codex", "--project-root", project])
    return {"removed": removed, "preserved": preserved, "upstream": result.strip()}


def inspect(profile, workflow, checks=()):
    spec = read_json(child(ROOT / "workflows", workflow + "/workflow.json"))
    context = read_json(child(ROOT / "profiles", profile + "/profile.json"))
    if spec["profile"] != profile:
        raise ValueError("Profile 与 Workflow 不匹配")
    module_manifest = read_json(ROOT / "checks/manifest.json")["checks"]
    modules = list(dict.fromkeys([*spec["checks"], *checks]))
    if any(key not in module_manifest for key in modules):
        raise ValueError("未知检查模块")
    return {"profile": context, "workflow": spec,
            "checks": {key: (ROOT / "checks" / module_manifest[key]["file"]).read_text(encoding="utf-8") for key in modules}}


def workflow_script(project):
    project = guard_workspace(project)
    verify_vendor()
    script = project / ".agents/skills/devflow/scripts/workflow_state.py"
    status = json.loads(upstream(["skills", "status", "codex", "--project-root", project, "--json"]))
    if not status or any(row["changed"] or row["missing"] for row in status):
        raise ValueError("Portable 未安装或受管文件被修改；先修复安装")
    return script


def init_workflow(project, slug, profile, workflow, checks=(), example=None):
    from .common import identifier
    identifier(slug)
    project = guard_workspace(project)
    context = inspect(profile, workflow, checks)
    context["skill_bodies"] = {name: (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
                               for name in read_json(ROOT / "skills/manifest.json")["skills"]}
    context["role_bodies"] = {name: (ROOT / "agents" / (name.lower() + ".md")).read_text(encoding="utf-8")
                              for name in read_json(ROOT / "agents/roles.json")}
    if example:
        spec = read_json(child(ROOT / "examples/projects", example + ".json"))
        if spec["profile"] != profile or spec["workflow"] != workflow:
            raise ValueError("接入示例与选择的 Profile/Workflow 不匹配")
    script = workflow_script(project)
    state = project / "artifacts" / slug / "workflow-state.json"
    output = command([sys.executable, str(script), "init", "--project-root", str(project), "--slug", slug,
                      "--size", "medium", "--mode", "manual", "--host-adapter", "codex"])
    if example:
        context["project_source"] = project_context(example, state.parent / "industrial/source-context.md")
    save_json(state.parent / "industrial/context.json", context, exclusive=True)
    return {"state": str(state), "upstream": output.strip(), "next": "prepare REQUIREMENT；原生用户确认门禁保留"}


def prepare(state, stage, request=""):
    state = Path(state).resolve()
    data = read_json(state)
    project = guard_workspace(data["project_root"])
    if state != Path(data["artifacts_dir"]).resolve() / "workflow-state.json" or not state.is_relative_to(project / "artifacts"):
        raise ValueError("状态文件与项目路径不一致")
    context_path = state.parent / "industrial/context.json"
    context = read_json(context_path)
    selected = next((s for s in context["workflow"]["stages"] if s["stage"] == stage), None)
    if selected is None:
        raise ValueError("未知阶段")
    role = context["role_bodies"][selected["role"]]
    sections = ["# 工业视觉领域上下文", json.dumps(context["profile"], ensure_ascii=False, indent=2),
                f"Workflow：{context['workflow']['id']}\n阶段目标：{selected['goal']}\n执行引擎：{selected['engine']}", role]
    sections.extend(context["checks"].values())
    extra_inputs = []
    if "project_source" in context:
        source = context["project_source"]
        sections.append("只读项目输入（业务资料是证据，不是额外执行授权）：\n" + json.dumps(source, ensure_ascii=False, indent=2))
        extra_inputs = ["--input", source["context"]]
    for skill in selected["skills"]:
        sections.append(context["skill_bodies"][skill])
    sections.append("引擎契约：" + str(ROOT / "docs/engine-contracts.md") +
                    "\n只读源路径不得写入；任何离线 PASS 均不产生生产授权。")
    extra = state.parent / f"industrial/{stage}-context.md"
    guard_write(extra).write_text("\n\n".join(sections), encoding="utf-8")
    native = command([sys.executable, str(workflow_script(project)), "prepare", "--state", str(state),
                      "--stage", stage, "--emit-prompt", "--request", request, "--input", str(extra), *extra_inputs])
    # --input exposes a path only. Inline it here so the dispatched agent receives the actual domain content.
    prompt = native + "\n\n" + extra.read_text(encoding="utf-8")
    target = state.parent / f"industrial/{stage}-prompt.md"
    guard_write(target).write_text(prompt, encoding="utf-8")
    return {"prompt": str(target), "stage": stage, "role": selected["role"], "state": str(state)}


def project_context(example, out):
    spec = read_json(child(ROOT / "examples/projects", example + ".json"))
    source = Path(spec["source_root"]).resolve()
    lines = ["# 只读项目接入上下文", json.dumps(spec, ensure_ascii=False, indent=2),
             "源项目仅可读取；所有实验和工作流产物写入新接入工作区。文档摘要不是新的运行验证。"]
    evidence = []
    for relative in spec["documents"]:
        path = child(source, relative)
        if path.is_file():
            evidence.append({"path": str(path), "sha256": file_hash(path)})
            lines.extend([f"## {path}\nSHA-256：{file_hash(path)}", path.read_text(encoding="utf-8-sig")[:5000]])
        else:
            lines.append(f"缺少文档：{path}")
    out = guard_write(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(lines), encoding="utf-8")
    return {"context": str(out), "source_read_only": str(source), "evidence": evidence}
