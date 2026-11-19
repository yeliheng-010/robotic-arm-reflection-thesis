"""拟合完成后才读真值；保留拒绝和所有回归。"""
import numpy as np
from visibility_calibration_v1.analysis import accuracy, summary
from visibility_calibration_v1.policy import THRESHOLDS
from pose_replay_v1.common import ROOT, folders, truth_path, read, save


def annotate(rows, originals, truth):
    keys = lambda row: (tuple(row.get("indices", [row.get("index")])), row["repeat"])
    indexed = {keys(row): row for row in originals}
    output = []
    for row in rows:
        old = indexed[keys(row)]
        output.append(dict(row, **accuracy(row["fit"], truth), visibility=old["visibility"],
                           full_frame_other_gates=old["full_frame_other_gates"]))
    return output


def transitions(old, new):
    assert len(old) == len(new)
    return dict(correct_to_incorrect=sum(a["accurate"] and not b["accurate"] for a, b in zip(old, new)),
                incorrect_to_correct=sum(not a["accurate"] and b["accurate"] for a, b in zip(old, new)),
                newly_false_accepted=sum(b["quality_passed"] and not b["accurate"]
                                        and not (a["quality_passed"] and not a["accurate"])
                                        for a, b in zip(old, new)))


def compare(old, new):
    return dict(original=summary(old), candidate=summary(new), transitions=transitions(old, new),
                original_frame_gate_accepted=sum(r["full_frame_other_gates"] for r in new),
                full_cloud_p95_over_limit=sum(r.get("full_cloud_p95_m", 0.) is not None
                    and r.get("full_cloud_p95_m", 0.) > .006 for r in new),
                thresholds=[dict(threshold=t, candidate=summary([r for r in new if r["visibility"] >= t]))
                            for t in THRESHOLDS])


def main():
    assert read(ROOT / "fitted.json")["inputs_unchanged"]
    report = {}
    for name, folder in folders().items():
        original = read(folder / "private_errors.json")
        fits = read(ROOT / f"{name}_fits.json")
        truth = read(truth_path(name, folder))
        rows = {kind: annotate(fits[kind], original[kind], truth) for kind in ("singles", "pairs")}
        save(ROOT / f"{name}_private_errors.json", rows)
        report[name] = {kind: compare(original[kind], rows[kind]) for kind in rows}
    save(ROOT / "analysis.json", dict(groups=report, independent_layouts=1, deployed=False,
         release_authorized=False, training_eligible=False, physical_task_success_rate=None))
    print({name: {kind: data["candidate"] for kind, data in group.items()} for name, group in report.items()}, flush=True)


if __name__ == "__main__":
    main()
