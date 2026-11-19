"""独立进程复算代表点云并核对完整统计、源码范围及输入哈希。"""
import ast
import json
import unittest
from unittest.mock import patch

import numpy as np
from held_observation_v1 import geometry
from pose_identifiability_v1 import robust
from pose_identifiability_v1.compare import summarize
from pose_identifiability_v1.diagnose import PROJECT, ROOT, SOURCE, save, sha
from pose_identifiability_v1.objective_probe import errors


def regression_tests():
    names = ("pose_identifiability_v1.test_candidate", "pose_identifiability_v1.test_rules",
             "held_observation_v1.test_geometry")
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in names)
    original = unittest.TextTestRunner(verbosity=1).run(suite)
    with patch.object(geometry, "fit", robust.fit):
        suite = unittest.defaultTestLoader.loadTestsFromName("held_observation_v1.test_geometry")
        robust_result = unittest.TextTestRunner(verbosity=1).run(suite)
    assert original.wasSuccessful() and robust_result.wasSuccessful()
    return dict(original_and_new=original.testsRun, robust_pipeline=robust_result.testsRun)


def independent_metrics(rows):
    truth_path = PROJECT / "visibility_calibration_v1/evidence/remote/phases/before_release/private_truth.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    raw_p95 = []
    for row in rows:
        fitted = row["fit"]
        center_error = np.linalg.norm(np.asarray(fitted["center"]) - truth["center"])
        dot = abs(np.dot(fitted["axis"], truth["axis"]))
        axis_error = np.degrees(np.arccos(np.clip(dot, 0., 1.)))
        assert abs(center_error - row["center_error_m"]) < 1e-12
        assert abs(axis_error - row["axis_error_deg"]) < 1e-10
        assert row["accurate"] == bool(center_error <= .010 and axis_error <= 12.)
        if row["variant"] == "filtered":
            with np.load(SOURCE / f'view_{row["index"]}/clouds.npz') as arrays:
                points = geometry.sample(arrays[f'noise_{row["repeat"]}'])
            p95 = float(np.percentile(np.abs(errors(points, fitted)), 95))
            assert p95 <= .006
            raw_p95.append(p95)
    return dict(classifications_checked=len(rows), full_unfiltered_cloud_checks=len(raw_p95),
                maximum_full_cloud_p95_m=max(raw_p95))


def representative_replay(rows):
    checked = []
    for row in rows:
        if row["variant"] != "filtered" or row["repeat"] not in (0, 10, 19):
            continue
        with np.load(SOURCE / f'view_{row["index"]}/clouds.npz') as arrays:
            actual = robust.fit(geometry.sample(arrays[f'noise_{row["repeat"]}']))
        assert actual == row["fit"]
        checked.append(dict(index=row["index"], repeat=row["repeat"], identical=True))
    assert len(checked) == 9
    return checked


def source_structure():
    files = []
    for path in ROOT.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 300, path.name
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, (path.name, node.name)
                assert len(node.args.args) <= 3, (path.name, node.name)
        files.append(path.name)
    return files


def main():
    tests = regression_tests()
    manifest = json.loads((ROOT / "comparison_manifest.json").read_text(encoding="utf-8"))
    for relative, digest in manifest["identities"].items():
        assert sha(PROJECT / relative) == digest, relative
    stored = json.loads((ROOT / "comparison_private_errors.json").read_text(encoding="utf-8"))
    summaries = json.loads((ROOT / "comparison_summary.json").read_text(encoding="utf-8"))
    assert summarize(stored["rows"]) == summaries["rows"]
    checks = representative_replay(stored["rows"])
    result = dict(passed=True, tests=tests, independent_fit_checks=checks,
                  independent_metrics=independent_metrics(stored["rows"]),
                  source_files=source_structure(), original_inputs_unchanged=True,
                  all_240_fit_statistics_rechecked=True, selected_variant="filtered",
                  physical_attempts=0, model_calls=0, training_runs=0,
                  deployed=False, release_authorized=False, independent_layouts=1)
    save(ROOT / "FINAL_VERIFICATION.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
