"""原版、轴向起点、过滤、过滤+起点的同点云消融；真值仅后处理。"""
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from held_observation_v1.geometry import fit as original_fit, sample
from visibility_calibration_v1.analysis import accuracy, single_quality
from pose_identifiability_v1.candidate import fit, fit_multistart, observed_inliers
from pose_identifiability_v1.diagnose import PROJECT, ROOT, SOURCE, VIEWS, save, sha

VARIANTS = ("original", "multistart", "filtered", "filtered_multistart")
TRUTH = PROJECT / "visibility_calibration_v1/evidence/remote/phases/before_release/private_truth.json"


def filtered_original(points):
    selected, filtering = observed_inliers(points)
    return dict(original_fit(selected), filtering=filtering)


def run_fits():
    solvers = (original_fit, fit_multistart, filtered_original, fit)
    rows = []
    for index in VIEWS:
        with np.load(SOURCE / f"view_{index}/clouds.npz") as arrays:
            clouds = [sample(arrays[f"noise_{repeat}"]) for repeat in range(20)]
        for repeat, points in enumerate(clouds):
            for name, solver in zip(VARIANTS, solvers):
                started = perf_counter()
                value = solver(points)
                rows.append(dict(index=index, repeat=repeat, variant=name, fit=value,
                                 seconds=perf_counter() - started))
        print(f"Finished view {index}: 20 existing clouds x 4 variants", flush=True)
    save(ROOT / "comparison_fits.json", dict(rows=rows, truth_available_to_fitter=False))
    return rows


def summarize(rows):
    summary = []
    for index in VIEWS:
        for variant in VARIANTS:
            group = [r for r in rows if r["index"] == index and r["variant"] == variant]
            accepted = [r for r in group if r["quality_passed"]]
            summary.append(dict(index=index, variant=variant, count=len(group),
                accurate=sum(r["accurate"] for r in group), accepted=len(accepted),
                false_accepted=sum(not r["accurate"] for r in accepted),
                center_error_median_mm=float(np.median([r["center_error_m"]*1000 for r in group])),
                center_error_max_mm=max(r["center_error_m"]*1000 for r in group),
                removed_range=[min(r["fit"].get("filtering", {}).get("removed_points", 0) for r in group),
                               max(r["fit"].get("filtering", {}).get("removed_points", 0) for r in group)],
                total_seconds=sum(r["seconds"] for r in group)))
    return summary


def evaluate(rows):
    # 拟合已落盘后，才加载独立真值评价，禁止回传给任何solver。
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    stored = json.loads((SOURCE / "private_errors.json").read_text(encoding="utf-8"))["singles"]
    old = {(r["index"], r["repeat"]): r for r in stored}
    deltas = []
    for row in rows:
        row.update(accuracy(row["fit"], truth), quality_passed=bool(single_quality(row["fit"])))
        if row["variant"] == "original":
            prior = old[row["index"], row["repeat"]]
            deltas.append(dict(index=row["index"], repeat=row["repeat"],
                accuracy_same=prior["accurate"] == row["accurate"],
                quality_same=prior["quality_passed"] == row["quality_passed"],
                center_delta_m=float(np.linalg.norm(np.array(prior["fit"]["center"]) - row["fit"]["center"]))))
    save(ROOT / "comparison_private_errors.json", dict(rows=rows, historical_comparison=deltas))
    return summarize(rows), deltas


def main():
    if (ROOT / "comparison_fits.json").exists():
        raise RuntimeError("已存在拟合结果；禁止无痕重跑，请先检查结果")
    paths = [SOURCE / f"view_{i}/clouds.npz" for i in VIEWS]
    paths += [PROJECT / "held_observation_v1/geometry.py", ROOT / "candidate.py", TRUTH]
    identities = {str(p.relative_to(PROJECT)): sha(p) for p in paths}
    save(ROOT / "comparison_manifest.json", dict(identities=identities, variants=VARIANTS,
         existing_clouds=60, independent_layouts=1, additional_simulation_frames=0,
         physical_task_attempts=0, model_calls=0, training_runs=0))
    summaries, deltas = evaluate(run_fits())
    assert identities == {str(p.relative_to(PROJECT)): sha(p) for p in paths}
    save(ROOT / "comparison_summary.json", dict(rows=summaries, input_hashes_unchanged=True,
         historical_classification_matches=all(r["accuracy_same"] and r["quality_same"] for r in deltas),
         max_historical_center_delta_m=max(r["center_delta_m"] for r in deltas),
         threshold_deployed=False, release_authorized=False, training_eligible=False))
    print(json.dumps(summaries), flush=True)


if __name__ == "__main__":
    main()
