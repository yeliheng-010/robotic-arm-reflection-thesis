"""Four methods, paired seeds, separated cold/warm memory results, CSV and plots."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics

from reflection.__main__ import add_options, bootstrap, build_engine

PROTOCOL_VERSION = 2


def episode_row(result, directory, episode):
    records = result["records"]
    visuals = [r["visual"] for r in records if r.get("visual")]
    first = records[0]["physical_success"]
    physical = records[-1]["physical_success"]
    stats = result.get("llm_stats", {})
    return {"method": result["method"], "source": result["source"],
            "destination": result["destination"], "fault": result["fault"],
            "episode": episode, "seed": result["seed"],
            "memory_phase": "cold" if episode == 1 else "subsequent",
            "success": result["success"], "physical_success": physical,
            "first_attempt_success": first, "initial_failure": not first,
            "recovered": bool(not first and physical),
            "attempts": result["attempts"], "elapsed_s": result["elapsed_s"],
            "memory_hit": result["memory_hit"], "perception": result["perception"],
            "segmentation": result["segmentation"], "reflector": result["reflector"],
            "reflection_errors": sum("reflection_error" in r for r in records),
            "visual_api_errors": sum(v.get("status") == "api_error" for v in visuals),
            "visual_invalid_responses": sum(v.get("status") == "invalid_response" for v in visuals),
            "visual_unknown": sum(v.get("success") is None for v in visuals),
            "visual_vetoes": sum(r["physical_success"] and r.get("visual", {}).get("success") is False
                                 for r in records if r.get("visual")),
            "llm_calls": stats.get("calls", 0), "api_latency_s": stats.get("latency_s", 0),
            "cache_hits": stats.get("cache_hits", 0),
            "scene_jitter_m": result.get("scene_jitter_m", 0),
            "result_path": str(directory / "result.json")}


def service_failed(result):
    return any(r.get("reflection_status") == "api_error" or
               (r.get("visual") or {}).get("status") == "api_error" or
               (r.get("error") or {}).get("evidence", {}).get("service_error")
               for r in result["records"])


def attempt_rows(result, directory, episode):
    rows = []
    for record in result["records"]:
        error = record.get("error") or {}
        rows.append({"method": result["method"], "source": result["source"],
                     "fault": result["fault"], "episode": episode, "seed": result["seed"],
                     "attempt": record["attempt"], "physical_success": record["physical_success"],
                     "accepted": record["accepted"], "last_stage": record["last_stage"],
                     "error_type": error.get("error_type", ""),
                     "error": json.dumps(error, ensure_ascii=False),
                     "parameters": json.dumps(record["parameters"], ensure_ascii=False),
                     "reflection": json.dumps(record.get("reflection"), ensure_ascii=False),
                     "reflection_error": record.get("reflection_error", ""),
                     "visual": json.dumps(record.get("visual"), ensure_ascii=False),
                     "before_image": str(directory / f"attempt_{record['attempt']}" / "before.png"),
                     "after_image": str(directory / f"attempt_{record['attempt']}" / "after.png")})
    return rows


def summarize(rows, fields=("method", "memory_phase")):
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[field] for field in fields), []).append(row)
    summary = []
    for key, values in groups.items():
        successes = sum(v["success"] for v in values)
        n = len(values)
        rate = successes/n
        z = 1.96
        denominator = 1+z*z/n
        center = (rate+z*z/(2*n))/denominator
        margin = z*((rate*(1-rate)/n+z*z/(4*n*n))**0.5)/denominator
        initial_failures = sum(v.get("initial_failure", False) for v in values)
        summary.append({**dict(zip(fields, key)), "episodes": n,
                        "success_rate": rate,
                        "physical_success_rate": sum(v["physical_success"] for v in values)/n,
                        "wilson_low": center-margin, "wilson_high": center+margin,
                        "mean_attempts": statistics.mean(v["attempts"] for v in values),
                        "mean_elapsed_s": statistics.mean(v["elapsed_s"] for v in values),
                        "memory_hits": sum(v["memory_hit"] for v in values),
                        "first_attempt_success_rate": sum(v.get("first_attempt_success", False) for v in values)/n,
                        "initial_failures": initial_failures,
                        "recovery_rate": sum(v.get("recovered", False) for v in values)/initial_failures if initial_failures else None,
                        "llm_calls": sum(v.get("llm_calls", 0) for v in values),
                        "api_latency_s": sum(v.get("api_latency_s", 0) for v in values),
                        "visual_api_errors": sum(v.get("visual_api_errors", 0) for v in values),
                        "visual_unknown": sum(v.get("visual_unknown", 0) for v in values),
                        "visual_vetoes": sum(v.get("visual_vetoes", 0) for v in values)})
    return summary


def write_csv(path, rows):
    if not rows:
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def export_results(output, rows, attempts, *, plot=False):
    write_csv(output / "episodes.csv", rows)
    write_csv(output / "attempts.csv", attempts)
    summary = summarize(rows)
    write_csv(output / "summary.csv", summary)
    write_csv(output / "summary_by_fault.csv", summarize(rows, ("method", "source", "fault", "memory_phase")))
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    if plot and summary:
        plot_summary(output, summary)
    return summary


def plot_summary(output, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = [r["method"]+"\n"+r["memory_phase"] for r in summary]
    colors = {"baseline": "#377eb8", "retry": "#4daf4a",
              "reflection": "#e41a1c", "reflection_memory": "#984ea3"}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), layout="constrained")
    for ax, field, label in zip(axes, ("success_rate", "mean_attempts", "mean_elapsed_s"),
                               ("Accepted success rate", "Attempts per episode", "Wall time (s)")):
        ax.bar(range(len(summary)), [r[field] for r in summary], color=[colors[r["method"]] for r in summary])
        ax.set_xticks(range(len(summary)), labels, fontsize=8, rotation=40, ha="right")
        ax.set_ylabel(label)
        if field == "success_rate":
            ax.set_ylim(0, 1.05)
        ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(output / "comparison.png", dpi=160)
    plt.close(fig)


def main(argv=None):
    bootstrap()
    from reflection.engine import METHODS
    from reflection.fault_injection import FAULTS
    from reflection.memory import ExperienceMemory
    parser = argparse.ArgumentParser(description=__doc__)
    add_options(parser)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--faults", nargs="+", choices=FAULTS,
                        default=["none", "planning", "grounding", "calibration", "collision", "slip", "placement"])
    parser.add_argument("--sources", nargs="+", choices=("RedBlock", "GreenCylinder", "PurpleCapsule", "OrangeSphere"),
                        default=["RedBlock"])
    parser.add_argument("--destination", default="BlueBin")
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scene-jitter", type=float, default=0.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-on-api-error", action="store_true")
    parser.add_argument("--output", default="logs/reflection/benchmark")
    args = parser.parse_args(argv)
    if args.episodes < 1:
        parser.error("episodes must be positive")
    if not math.isfinite(args.scene_jitter) or not 0 <= args.scene_jitter <= 0.015:
        parser.error("scene-jitter must be in [0, 0.015] metres")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = {k: v for k, v in vars(args).items() if k not in {"output", "resume"}}
    config["protocol_version"] = PROTOCOL_VERSION
    config_path = output / "config.json"
    if config_path.exists():
        if not args.resume:
            parser.error("output already contains a run; use --resume or a new --output")
        if json.loads(config_path.read_text()) != config:
            parser.error("resume configuration differs from the original run")
    elif args.resume:
        parser.error("no config.json found to resume")
    elif any(output.iterdir()):
        parser.error("new benchmark output must be empty")
    else:
        config_path.write_text(json.dumps(config, indent=2))
    rows, attempts = [], []
    total = len(args.methods)*len(args.sources)*len(args.faults)*args.episodes
    exit_code = 0
    try:
        for method in args.methods:
            for source in args.sources:
                for scenario_number, fault in enumerate(args.faults):
                    context = f"setup-{scenario_number}"
                    database = output / "memory" / f"{method}-{source}-{scenario_number}.sqlite3"
                    memory = ExperienceMemory(database)
                    engine = None
                    try:
                        for episode in range(1, args.episodes+1):
                            directory = output / method / source / fault / f"episode_{episode}"
                            result_path = directory / "result.json"
                            checkpoint = directory / "memory_before.sqlite3"
                            if result_path.exists():
                                result = json.loads(result_path.read_text())
                            else:
                                if checkpoint.exists():
                                    memory.restore(checkpoint)
                                else:
                                    memory.checkpoint(checkpoint)
                                if engine is None:
                                    engine = build_engine(args, memory)
                                result = engine.run(source=source, destination=args.destination, fault=fault,
                                                    method=method, context=context, output=directory,
                                                    seed=args.seed+episode-1)
                            if args.stop_on_api_error and service_failed(result):
                                result_path.replace(directory / "service_error.json")
                                memory.restore(checkpoint)
                                raise RuntimeError(f"Model service unavailable: {directory}; resume after restoring service")
                            rows.append(episode_row(result, directory, episode))
                            attempts.extend(attempt_rows(result, directory, episode))
                            export_results(output, rows, attempts)
                            print(f"[progress] {len(rows)}/{total} {method} {source} {fault} episode={episode}", flush=True)
                    finally:
                        if engine is not None:
                            engine.close()
                            if engine.client is not None:
                                engine.client.close()
                        memory.close()
    except KeyboardInterrupt:
        print("Interrupted; completed episodes are preserved. Use --resume.", flush=True)
        exit_code = 130
    except (RuntimeError, ValueError) as exc:
        print(str(exc), flush=True)
        exit_code = 1
    finally:
        summary = export_results(output, rows, attempts, plot=True)
        (output / "status.json").write_text(json.dumps({"completed": len(rows), "total": total,
                                                       "complete": len(rows) == total and exit_code == 0,
                                                       "exit_code": exit_code}, indent=2))
    for row in summary:
        print(f"{row['method']:20} {row['memory_phase']:10} success={row['success_rate']:.1%} "
              f"attempts={row['mean_attempts']:.2f} seconds={row['mean_elapsed_s']:.2f}")
    print(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
