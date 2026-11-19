from pose_crossview_v1.run import ROOT, REPLAY, sources, compute, verify_pair, input_identities
from pose_replay_v1.common import identities, read, save, truth_path
from visibility_calibration_v1.analysis import accuracy, summary


def main():
    before = read(ROOT / "started.json")["inputs"]
    assert before == input_identities()
    rows = read(ROOT / "fits.json")["rows"]
    truth = read(truth_path("before_release", sources()["before_release"]))
    annotated = []
    for row in rows:
        assert verify_pair(row["views"]) == row["angle_deg"]
        actual = compute(row["views"], row["repeat"])
        expected = {k: v for k, v in row.items() if k not in ("pair_index", "views", "repeat", "angle_deg")}
        assert actual == expected
        annotated.append(dict(row, **accuracy(actual["fit"], truth)))
    assert annotated == read(ROOT / "private_errors.json")["rows"]
    analysis = read(ROOT / "analysis.json")
    assert summary(annotated) == analysis["overall"]
    assert before == input_identities()
    save(ROOT / "audit.json", dict(passed=True, independent_pair_checks=len(rows),
         inputs_unchanged=True, physical_success_verified=False))
    print(dict(passed=True, independent_pair_checks=len(rows)), flush=True)


if __name__ == "__main__":
    main()
