"""Run the thesis protocol in headless stages with isolated data and resume."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid

from reflection.__main__ import bootstrap
from experiments.run_benchmark import PROTOCOL_VERSION, write_csv

ROOT = Path(__file__).resolve().parents[1]
METHODS = ["baseline", "retry", "reflection", "reflection_memory"]
FAULTS = ["none", "planning", "grounding", "calibration", "collision", "slip", "placement"]
STAGES = {
    "smoke": {"reflector": "rule", "perception": "simulation", "segmentation": "simulation", "visual_verify": False},
    "mechanism": {"reflector": "llm", "perception": "simulation", "segmentation": "simulation", "visual_verify": False},
    "integrated": {"reflector": "llm", "perception": "vlm", "segmentation": "sam", "visual_verify": True},
    "verification_ablation": {"reflector": "llm", "perception": "vlm", "segmentation": "sam", "visual_verify": False},
}


def make_plan(profile, stages=None, episodes=None, seed=42, scene_jitter=0.008,
              methods=None, sources=None, faults=None, destination="BlueBin"):
    if destination not in {"BlueBin", "RedBin", "SortingTray"}:
        raise ValueError("destination must be BlueBin, RedBin, or SortingTray")
    names = ["smoke"] if profile == "smoke" else ["mechanism", "integrated", "verification_ablation"]
    if stages:
        if not set(stages).issubset(names) or len(stages) != len(set(stages)):
            raise ValueError("stages must be distinct stages from the selected profile")
        names = [name for name in names if name in stages]
    plan = []
    for name in names:
        count = episodes or (10 if profile == "thesis" and name == "mechanism" else
                             5 if profile == "thesis" else 2)
        defaults = {"sources": ["RedBlock"] if name == "smoke" else ["RedBlock", "GreenCylinder"],
                    "faults": ["calibration", "collision", "placement"] if name == "smoke" else list(FAULTS),
                    "methods": list(METHODS)}
        selected = {}
        for key, values in (("methods", methods), ("sources", sources), ("faults", faults)):
            if values is not None and (not values or len(values) != len(set(values)) or
                                       not set(values).issubset(defaults[key])):
                raise ValueError(f"{key} must be distinct selections from {name}: {defaults[key]}")
            selected[key] = list(values) if values is not None else defaults[key]
        plan.append({"name": name, **STAGES[name], **selected, "episodes": count, "seed": seed,
                     "scene_jitter": scene_jitter, "max_attempts": 3,
                     "destination": destination, "grasp_backend": "geometric",
                     "tasks": len(selected["sources"])*len(selected["faults"])*len(selected["methods"])*count})
    return plan


def stage_command(stage, output, resume=False):
    command = [sys.executable, "-u", "-m", "experiments.run_benchmark", "--headless",
               "--stop-on-api-error", "--task-parser", "rule", "--output", str(output)]
    for name in ("reflector", "perception", "segmentation", "episodes", "seed",
                 "scene_jitter", "max_attempts", "destination", "grasp_backend"):
        command.extend(["--"+name.replace("_", "-"), str(stage[name])])
    for name in ("sources", "faults", "methods"):
        command.extend(["--"+name, *stage[name]])
    if stage["visual_verify"]:
        command.append("--visual-verify")
    if resume:
        command.append("--resume")
    return command


def code_fingerprints():
    paths = list((ROOT / "reflection").glob("*.py")) + list((ROOT / "experiments").glob("*.py"))
    paths += [ROOT / "manipulator_grasp/env/ur5_grasp_env.py", ROOT / "manipulator_grasp/utils/mj.py", ROOT / "grasp_process.py",
              ROOT / "vlm_process.py", ROOT / "run_experiments.sh", ROOT / "experiments/PROTOCOL.md"]
    paths += list((ROOT / "manipulator_grasp/assets/scenes").glob("*.xml"))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def environment_info():
    versions = {}
    for package in ("mujoco", "numpy", "torch", "openai", "ultralytics", "opencv-python", "matplotlib"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    changes = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
    return {"python": sys.version, "executable": sys.executable, "packages": versions,
            "git_commit": revision.stdout.strip(), "git_dirty": bool(changes.stdout.strip()),
            "code_sha256": code_fingerprints(), "mujoco_gl": os.environ.get("MUJOCO_GL"),
            "llm_response_cache": False, "recorded_at": datetime.now(timezone.utc).isoformat()}


def preflight(plan):
    bootstrap()
    # Exercise the actual renderer, not just import availability.
    import mujoco
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    from grasp_process import run_grasp_inference  # noqa: F401
    env = UR5GraspEnv(headless=True)
    try:
        env.reset()
        frame = env.render()["img"]
        if frame.size == 0 or frame.max() == frame.min():
            raise RuntimeError("Offscreen renderer returned a blank image")
    finally:
        env.close()
    info = {"renderer": "EGL", "frame_size": list(frame.shape), "mujoco": mujoco.__version__}
    if any(stage["reflector"] == "llm" for stage in plan):
        from reflection.llm import LLMClient
        client = LLMClient(use_cache=False)
        try:
            info["model_id"] = client.model
            info["model_credentials_present"] = True
        finally:
            client.close()
    if any(stage["segmentation"] == "sam" for stage in plan):
        weight = ROOT / "sam_b.pt"
        if not weight.is_file():
            raise RuntimeError("Missing sam_b.pt; integrated stages require the existing SAM weights")
        from vlm_process import choose_model
        choose_model()
        info["sam_weights"] = {"file": weight.name, "bytes": weight.stat().st_size,
                               "sha256": hashlib.sha256(weight.read_bytes()).hexdigest()}
    return info


def collect_results(output, plan):
    episodes, summaries = [], []
    completed = 0
    for stage in plan:
        directory = output / stage["name"]
        for filename, target in (("episodes.csv", episodes), ("summary_by_fault.csv", summaries)):
            path = directory / filename
            if path.exists():
                with path.open(newline="", encoding="utf-8") as stream:
                    target.extend({"stage": stage["name"], **row} for row in csv.DictReader(stream))
        status = directory / "status.json"
        if status.exists():
            completed += json.loads(status.read_text())["completed"]
    write_csv(output / "suite_episodes.csv", episodes)
    write_csv(output / "suite_summary_by_fault.csv", summaries)
    total = sum(stage["tasks"] for stage in plan)
    lines = ["# Experiment Run", "", f"Completed: {completed}/{total} tasks", "",
             "- Protocol: experiments/PROTOCOL.md", "- Configuration and environment: manifest.json",
             "- All episodes: suite_episodes.csv", "- Per-condition summary: suite_summary_by_fault.csv",
             "- Per-stage: episodes.csv, attempts.csv, summary.csv, comparison.png",
             "- Each episode: result.json and attempt_N/before.png, after.png, mask.png, plan.json", "",
             "Physical success and accepted success are separate. Cold and subsequent memory results are separate.",
             "Service errors are excluded from completed episodes and retained in service_error.json.",
             "Retries restore the same initial scene; detection uses simulation ground truth.", ""]
    (output / "REPORT.md").write_text("\n".join(lines))
    return completed, total


def run_stage(command, logfile):
    logfile.parent.mkdir(parents=True, exist_ok=True)
    with logfile.open("a", encoding="utf-8") as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
        try:
            for line in process.stdout:
                print(line, end="", flush=True)
                stream.write(line)
                stream.flush()
            return process.wait()
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            return 130
        finally:
            process.stdout.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("smoke", "pilot", "thesis"))
    parser.add_argument("--stages", nargs="+", choices=STAGES)
    parser.add_argument("--methods", nargs="+", choices=METHODS)
    parser.add_argument("--sources", nargs="+", choices=("RedBlock", "GreenCylinder"))
    parser.add_argument("--destination", choices=("BlueBin", "RedBin", "SortingTray"))
    parser.add_argument("--faults", nargs="+", choices=FAULTS)
    parser.add_argument("--episodes", type=int, help="Override episodes per condition for selected stages")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--scene-jitter", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", type=Path, metavar="RUN_DIRECTORY")
    parser.add_argument("--dry-run", action="store_true", help="Print the matrix without simulation or model calls")
    parser.add_argument("--check-only", action="store_true", help="Check dependencies and rendering without running tasks")
    args = parser.parse_args(argv)
    if args.episodes is not None and args.episodes < 1:
        parser.error("episodes must be positive")
    if args.scene_jitter is not None and not 0 <= args.scene_jitter <= 0.015:
        parser.error("scene-jitter must be in [0, 0.015] metres")
    if args.resume and args.output:
        parser.error("use either --resume or --output")
    os.environ["MUJOCO_GL"] = "egl"
    os.environ["REFLECTION_LLM_CACHE"] = "0"
    os.chdir(ROOT)
    if args.resume:
        output = args.resume.resolve()
        path = output / "manifest.json"
        if not path.exists():
            parser.error("resume directory has no manifest.json")
        manifest = json.loads(path.read_text())
        if manifest["protocol_version"] != PROTOCOL_VERSION:
            parser.error("cannot resume a different protocol version")
        config = manifest["configuration"]
        for key in ("profile", "stages", "episodes", "seed", "scene_jitter", "methods", "sources", "faults", "destination"):
            provided = getattr(args, key)
            if provided is not None and provided != config.get(key):
                parser.error(f"--{key.replace('_', '-')} differs from saved configuration")
        plan = manifest["plan"]
        if manifest["environment"]["code_sha256"] != code_fingerprints():
            parser.error("experiment code changed since this run; use a new output directory")
    else:
        config = {"profile": args.profile or "smoke", "stages": args.stages, "episodes": args.episodes,
                  "seed": args.seed if args.seed is not None else 42,
                  "scene_jitter": args.scene_jitter if args.scene_jitter is not None else 0.008,
                  "methods": args.methods, "sources": args.sources, "faults": args.faults,
                  "destination": args.destination or "BlueBin"}
        try:
            plan = make_plan(**config)
        except ValueError as exc:
            parser.error(str(exc))
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        output = (args.output or ROOT / "logs/reflection/experiments" / f"{config['profile']}_{stamp}").resolve()
    total = sum(stage["tasks"] for stage in plan)
    for stage in plan:
        print(f"{stage['name']}: {len(stage['methods'])} methods x {len(stage['sources'])} objects x "
              f"{len(stage['faults'])} conditions x {stage['episodes']} episodes = {stage['tasks']} tasks", flush=True)
    print(f"Total: {total}; output: {output}; headless=EGL; response cache=off", flush=True)
    if args.dry_run:
        return 0
    try:
        check = preflight(plan)
        print(f"Preflight passed: {json.dumps(check)}", flush=True)
    except Exception as exc:
        print(f"Preflight failed: {exc}", file=sys.stderr)
        return 1
    if args.check_only:
        return 0
    if not args.resume:
        if output.exists() and any(output.iterdir()):
            parser.error("new suite output must be empty; use --resume for an existing run")
        output.mkdir(parents=True, exist_ok=True)
        manifest = {"protocol_version": PROTOCOL_VERSION, "configuration": config, "plan": plan,
                    "total_tasks": total, "environment": environment_info(), "preflight": check}
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    elif check.get("model_id") != manifest["preflight"].get("model_id"):
        parser.error("model ID changed since this run; use a new output directory")
    exit_code = 0
    try:
        for stage in plan:
            directory = output / stage["name"]
            status = directory / "status.json"
            if status.exists() and json.loads(status.read_text()).get("complete"):
                print(f"[skip] {stage['name']} already complete", flush=True)
                continue
            # Logs live at suite level so a fresh benchmark directory stays empty.
            command = stage_command(stage, directory, resume=(directory / "config.json").exists())
            print(f"[stage] {stage['name']}", flush=True)
            exit_code = run_stage(command, output / f"{stage['name']}.log")
            collect_results(output, plan)
            if exit_code:
                break
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        completed, total = collect_results(output, plan)
        print(f"Saved: {completed}/{total} tasks; {output}", flush=True)
    if exit_code:
        print(f'Continue: bash run_experiments.sh --resume "{output}"', flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
