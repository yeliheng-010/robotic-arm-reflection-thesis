"""从已有实验包导出公开统计；不运行仿真，不发布坐标或私有真值。"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "evidence/visibility_6495_6497"
PACKAGES = ("visibility_boundary_v1", "visibility_boundary_v2")
FIELDS = ("experiment", "view_index", "repeat", "visibility", "center_error_mm",
          "axis_error_deg", "accurate", "quality_passed", "fit_condition")


def read_source(root, relative, provenance):
    path = root / relative
    raw = path.read_bytes()
    provenance.append({"source": relative, "sha256": hashlib.sha256(raw).hexdigest()})
    return json.loads(raw)


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def collect_rows(root, provenance):
    rows = []
    for package in PACKAGES:
        source = read_source(root, f"{package}/evidence/remote/private_errors.json", provenance)
        for item in source["singles"]:
            row = dict(zip(FIELDS, (package, item["index"], item["repeat"],
                       item["visibility"], item["center_error_m"] * 1000,
                       item["axis_error_deg"], int(item["accurate"]),
                       int(item["quality_passed"]), item["fit"]["condition"])))
            assert row["accurate"] == int(row["center_error_mm"] <= 10 and row["axis_error_deg"] <= 12)
            rows.append(row)
    return rows


def validate_summary(rows, summaries):
    for item in summaries:
        group = [r for r in rows if r["experiment"] == item["experiment"]
                 and abs(r["visibility"] - float(item["visibility"])) < 1e-12]
        assert len(group) == int(item["noise_repeats"])
        assert sum(r["accurate"] for r in group) == int(item["accurate"])
        assert sum(r["quality_passed"] for r in group) == int(item["quality_accepted"])
        assert abs(median(r["center_error_mm"] for r in group) - float(item["median_center_error_mm"])) < 1e-9
        assert abs(max(r["center_error_mm"] for r in group) - float(item["max_center_error_mm"])) < 1e-9


def collect_audits(root, provenance):
    audits = []
    for package in ("visibility_calibration_v1", *PACKAGES):
        source = read_source(root, f"{package}/evidence/remote/audit.json", provenance)
        checks = source.get("checked")
        if checks is None:
            checks = [item for phase in source["phases"].values() for item in phase["pair_checks"]]
        assert all(item["identical"] for item in checks)
        audits.append({"experiment": package, "passed": source["passed"],
                       "checked_fits": len(checks)})
    assert all(a["passed"] for a in audits)
    assert sum(a["checked_fits"] for a in audits) == 45
    return audits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_root", type=Path)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = []
    rows = collect_rows(args.experiment_root, provenance)
    summary_path = args.experiment_root / "visibility_calibration_v1/release_visibility_curve.csv"
    summary_bytes = summary_path.read_bytes()
    summaries = list(csv.DictReader(summary_bytes.decode("utf-8-sig").splitlines()))
    validate_summary(rows, summaries)
    assert len(rows) == 192 and len(summaries) == 12
    with (OUT / "measurements.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary_text = "\n".join(summary_bytes.decode("utf-8-sig").splitlines()) + "\n"
    (OUT / "summary.csv").write_text(summary_text, encoding="utf-8", newline="\n")
    provenance.append({"source": "visibility_calibration_v1/release_visibility_curve.csv",
                       "sha256": hashlib.sha256(summary_bytes).hexdigest()})
    source = read_source(args.experiment_root, "visibility_calibration_v1/FINAL_VERIFICATION.json", provenance)
    snapshot = {key: value for key, value in source.items() if key != "documents"}
    snapshot["fit_audits"] = collect_audits(args.experiment_root, provenance)
    snapshot["boundary_rows"] = len(rows)
    snapshot["scope"] = "One development layout; simulated segmentation; no physical success claim"
    write_json("snapshot.json", snapshot)
    write_json("provenance.json", {"sources": provenance, "published_fields": FIELDS})
    print("Validated 192 measurements, 12 summaries and 45 independent fit checks.")


if __name__ == "__main__":
    main()
