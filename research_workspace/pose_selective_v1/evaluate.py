"""复用冻结记录评估原版优先策略，无新增拟合、物理或训练。"""
import hashlib
import json
from pathlib import Path
from pose_selective_v1.policy import choose

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
PHASES = ("preflight", "after_lift", "before_release", "boundary_v1", "boundary_v2")


def source(name):
    if name.startswith("boundary"):
        return PROJECT / f"visibility_{name}/evidence/remote/private_errors.json"
    return PROJECT / f"visibility_calibration_v1/evidence/remote/phases/{name}/private_errors.json"


def summarize(original, repaired):
    assert len(original) == len(repaired)
    counts = dict(total=len(original), original_kept=0, repair_accepted=0,
                  accepted=0, rejected=0, accurate_accepted=0, false_accepted=0,
                  original_accepted_lost=0, newly_false_accepted=0)
    choices = []
    for old, new in zip(original, repaired):
        assert (old.get("index"), old.get("indices"), old["repeat"]) == (
                new.get("index"), new.get("indices"), new["repeat"])
        choice = choose(old["quality_passed"], new["quality_passed"])
        row = old if choice == "original" else new if choice == "repaired" else None
        counts["original_kept"] += choice == "original"
        counts["repair_accepted"] += choice == "repaired"
        counts["accepted"] += row is not None
        counts["rejected"] += row is None
        counts["accurate_accepted"] += bool(row and row["accurate"])
        counts["false_accepted"] += bool(row and not row["accurate"])
        counts["original_accepted_lost"] += bool(old["quality_passed"] and choice != "original")
        counts["newly_false_accepted"] += bool(choice == "repaired" and not row["accurate"])
        choices.append(choice)
    counts["coverage"] = counts["accepted"] / counts["total"] if counts["total"] else None
    return dict(**counts, choices=choices)


def main():
    output, hashes = {}, {}
    for name in PHASES:
        old_path = source(name)
        new_path = PROJECT / f"pose_replay_v1/evidence/remote/{name}_private_errors.json"
        old, new = [json.loads(p.read_text(encoding="utf-8")) for p in (old_path, new_path)]
        output[name] = {kind: summarize(old[kind], new[kind]) for kind in ("singles", "pairs")}
        hashes.update({str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (old_path, new_path)})
    result = dict(groups=output, input_hashes=hashes, independent_layouts=1,
                  deployed=False, additional_fit_calls=0, physical_attempts=0, model_calls=0,
                  training_runs=0, high_success_threshold=None)
    with (ROOT / "analysis.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({name: {kind: {k: v for k, v in row.items() if k != "choices"}
                            for kind, row in group.items()} for name, group in output.items()}))


if __name__ == "__main__":
    main()
