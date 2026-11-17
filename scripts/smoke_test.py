"""Exercise Portable integration and the synthetic experiment/evaluation loop."""
import json
import os
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ivw.common import read_json, runtime_env, save_json, stamp
from scripts.protection_snapshot import snapshot


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run_smoke():
    output = ROOT / "local" / ("smoke-" + uuid.uuid4().hex)
    output.mkdir(parents=True)
    commands = []
    report = {"started_at": stamp(), "status": "failed", "evidence_level": "synthetic",
              "independent_agent_review": "not-run", "field_validation": "not-run",
              "production_authorized": False, "commands": commands}

    def command(args, expected=(0,)):
        args = list(map(str, args))
        result = subprocess.run(args, cwd=output, env=runtime_env(), capture_output=True, text=True, encoding="utf-8")
        index = len(commands) + 1
        (output / f"{index:03d}-stdout.log").write_text(result.stdout, encoding="utf-8")
        (output / f"{index:03d}-stderr.log").write_text(result.stderr, encoding="utf-8")
        commands.append({"argv": args, "returncode": result.returncode, "expected": list(expected)})
        require(result.returncode in expected, f"命令失败: {args}\n{result.stdout}\n{result.stderr}")
        try:
            return json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            return {"text": result.stdout.strip()}

    def cli(*args, expected=(0,), root=ROOT):
        return command([sys.executable, root / "ivw.py", *args], expected)

    def windows_script(name, flag, path, root=ROOT):
        return command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", root / "scripts" / name,
                        flag, path, "-Python", sys.executable])

    before = snapshot()
    save_json(output / "protected-before.json", before, exclusive=True)
    try:
        report["components"] = cli("validate")
        workspace = output / "接入 workspace"
        if os.name == "nt":
            windows_script("Install.ps1", "-Project", workspace)
        else:
            cli("install", "--project", workspace)
        status = cli("status", "--project", workspace)
        require(not status["extension_drift"], "专业 Skill 安装摘要不一致")
        cli("doctor", "--project", workspace)
        report["workflows"] = []
        for path in sorted((ROOT / "workflows").glob("*/workflow.json")):
            spec = read_json(path)
            args = ["init", "--project", workspace, "--slug", spec["id"], "--profile", spec["profile"], "--workflow", spec["id"]]
            example = {"sop-model-research": "sop", "pointcloud-error-diagnosis": "saddles"}.get(spec["id"])
            if example:
                args.extend(["--example", example])
            initialized = cli(*args)
            state = initialized["state"]
            prepared = cli("prepare", "--state", state, "--stage", "REQUIREMENT", "--request", "只读接入与合成验证")
            prompt = Path(prepared["prompt"]).read_text(encoding="utf-8")
            require(spec["profile"] in prompt and "vision-dataset-audit" in prompt, "领域上下文未进入真实 Prompt")
            cli("state", "validate", "--state", state)
            cli("state", "start", "--state", state, "--stage", "DESIGN", expected=(2,))
            cli("state", "approve", "--state", state, "--stage", "REQUIREMENT", expected=(2,))
            report["workflows"].append({"id": spec["id"], "state": state, "requirement_gate": "preserved"})

        store = output / "experiments"
        report["experiments"] = {}
        for task in ("sop", "detection", "saddles", "calibration"):
            variants = {}
            for variant in ("baseline", "candidate"):
                run = cli("experiment", "run", "--config", ROOT / f"examples/experiments/{task}-{variant}.json", "--store", store)
                evaluation = cli("evaluate", "--run", run["record"], "--dataset", ROOT / f"examples/datasets/{task}.json",
                                 "--protocol", ROOT / "examples/evaluation-protocol.json", "--store", store, expected=(0, 1))
                require(read_json(evaluation["report"])["evidence_level"] == "synthetic", "证据等级发生变化")
                variants[variant] = {"run": run, "evaluation": evaluation}
            variants["comparison"] = cli("evaluate", "--baseline", variants["baseline"]["evaluation"]["report"],
                                         "--candidate", variants["candidate"]["evaluation"]["report"])
            cli("experiment", "compare", "--baseline", variants["baseline"]["run"]["record"], "--candidate", variants["candidate"]["run"]["record"])
            report["experiments"][task] = variants
        calibration = report["experiments"]["calibration"]
        require(calibration["baseline"]["evaluation"]["verdict"] == "FAIL" and calibration["candidate"]["evaluation"]["verdict"] == "PASS", "标定训练改进闭环未成立")
        require(calibration["comparison"]["delta"]["center_error_max_m"] < -0.1, "标定中心误差未改善")
        sop = report["experiments"]["sop"]["candidate"]["evaluation"]
        require(sop["verdict"] == "FAIL" and sop["metrics"]["evidence_binding"] == 0.8, "证据绑定失败被错误放行")
        case = read_json(sop["report"])["failure_cases"][0]
        failure = {"sample_id": case["sample_id"], "stage": "evaluation", "expected": "证据绑定原始样本与对象时间",
                   "observed": case, "hypothesis": "低置信度事件携带错误 sample_id", "evidence_level": "synthetic",
                   "evaluation_report": sop["report"]}
        save_json(output / "failure.json", failure, exclusive=True)
        report["failure_record"] = cli("experiment", "failure", "--file", output / "failure.json", "--store", store)

        edited = workspace / ".agents/skills/vision-error-analysis/SKILL.md"
        edited.write_text("user-edited smoke fixture", encoding="utf-8")
        if os.name == "nt":
            uninstalled = windows_script("Uninstall.ps1", "-Project", workspace)
        else:
            uninstalled = cli("uninstall", "--project", workspace)
        require(".agents/skills/vision-error-analysis/SKILL.md" in uninstalled["preserved"], "卸载未保留用户修改")
        require(edited.read_text() == "user-edited smoke fixture" and (workspace / "artifacts").is_dir(), "卸载破坏用户产物")

        archive_path = output / "delivery.zip"
        if os.name == "nt":
            report["package"] = windows_script("Share.ps1", "-Output", archive_path)
        else:
            report["package"] = command([sys.executable, ROOT / "scripts/package.py", "--output", archive_path])
        relocated = output / "解压 portable"
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            require(not any(name.startswith(("local/", "workspaces/", ".agents/", ".devflow/", ".ivw/")) for name in names), "共享包混入本地状态")
            archive.extractall(relocated)
        cli("validate", root=relocated)
        relocated_workspace = output / "relocated workspace"
        cli("install", "--project", relocated_workspace, root=relocated)
        cli("doctor", "--project", relocated_workspace, root=relocated)
        relocated_run = cli("experiment", "run", "--config", relocated / "examples/experiments/calibration-candidate.json", "--store", output / "relocated-store", root=relocated)
        cli("evaluate", "--run", relocated_run["record"], "--dataset", relocated / "examples/datasets/calibration.json",
            "--protocol", relocated / "examples/evaluation-protocol.json", "--store", output / "relocated-store", root=relocated)
        report["relocation"] = "passed"
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        after = snapshot()
        save_json(output / "protected-after.json", after, exclusive=True)
        report["protected_projects_unchanged"] = before == after
        if before != after:
            report.update(status="failed", protection_error="只读项目的观察状态发生变化")
        report["finished_at"] = stamp()
        save_json(output / "report.json", report, exclusive=True)
    print(json.dumps({"status": report["status"], "report": str(output / "report.json"),
                      "protected_projects_unchanged": report["protected_projects_unchanged"], **({"error": report["error"]} if "error" in report else {})}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(run_smoke())
