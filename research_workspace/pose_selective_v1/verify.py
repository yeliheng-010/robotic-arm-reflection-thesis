"""独立本地核对冻结估计的误差与选择统计，不重跑远端求解。"""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np
from pose_selective_v1.evaluate import PROJECT, ROOT, PHASES, source


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_accuracy(rows, truth):
    for row in rows:
        fitted = row["fit"]
        if fitted is None:
            assert not row["accurate"] and row["center_error_m"] is None
            continue
        center = np.linalg.norm(np.asarray(fitted["center"]) - truth["center"])
        angle = np.degrees(np.arccos(np.clip(abs(np.dot(fitted["axis"], truth["axis"])), 0., 1.)))
        assert abs(center - row["center_error_m"]) < 1e-12
        assert abs(angle - row["axis_error_deg"]) < 1e-9
        assert row["accurate"] == bool(center <= .010 and angle <= 12.)


def verify_selection(old, new, report):
    accepted = []
    expected_choices = []
    for a, b in zip(old, new):
        if a["quality_passed"]:
            accepted.append(a)
            expected_choices.append("original")
        elif b["quality_passed"]:
            accepted.append(b)
            expected_choices.append("repaired")
        else:
            expected_choices.append(None)
    assert report["choices"] == expected_choices
    assert report["accepted"] == len(accepted)
    assert report["accurate_accepted"] == sum(r["accurate"] for r in accepted)
    assert report["false_accepted"] == sum(not r["accurate"] for r in accepted)
    assert report["original_accepted_lost"] == 0


def structure():
    checked = []
    for folder in ("pose_replay_v1", "pose_crossview_v1", "pose_selective_v1"):
        for path in (PROJECT / folder).glob("*.py"):
            code = path.read_text(encoding="utf-8")
            assert len(code.splitlines()) <= 300
            for node in ast.walk(ast.parse(code)):
                if isinstance(node, ast.FunctionDef):
                    assert node.end_lineno - node.lineno + 1 <= 50, node.name
                    assert len(node.args.args) <= 3, node.name
            checked.append(str(path.relative_to(PROJECT)))
    return checked


def main():
    report = read(ROOT / "analysis.json")
    for path, digest in report["input_hashes"].items():
        assert hashlib.sha256((PROJECT / path).read_bytes()).hexdigest() == digest
    verified = 0
    for name in PHASES:
        phase = "before_release" if name.startswith("boundary") else name
        truth = read(PROJECT / f"visibility_calibration_v1/evidence/remote/phases/{phase}/private_truth.json")
        original = read(source(name))
        candidate = read(PROJECT / f"pose_replay_v1/evidence/remote/{name}_private_errors.json")
        for kind in ("singles", "pairs"):
            verify_accuracy(candidate[kind], truth)
            verify_selection(original[kind], candidate[kind], report["groups"][name][kind])
            verified += len(candidate[kind])
    cross = read(PROJECT / "pose_crossview_v1/evidence/remote/private_errors.json")["rows"]
    verify_accuracy(cross, truth)
    assert verified == 477 and len(cross) == 15
    result = dict(passed=True, replay_estimates_checked=verified, crossview_estimates_checked=len(cross),
                  source_files=structure(), source_hashes_unchanged=True, deployed=False)
    (ROOT / "FINAL_VERIFICATION.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
