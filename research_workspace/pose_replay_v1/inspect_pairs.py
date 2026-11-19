"""只按相机角度和候选质量列出跨批次观察组合，不读取真值。"""
import json
from itertools import combinations
from pathlib import Path
from visibility_calibration_v1.policy import angle

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
MIN_ACCEPTED_FRACTION = .8
MIN_ANGLE_DEG = 10.


def collect():
    entries = []
    for name in ("before_release", "boundary_v1", "boundary_v2"):
        folder = (PROJECT / "visibility_calibration_v1/evidence/remote/phases/before_release"
                  if name == "before_release" else PROJECT / f"visibility_{name}/evidence/remote")
        views = json.loads((folder / "views.json").read_text(encoding="utf-8"))
        fitted = json.loads((ROOT / f"evidence/remote/{name}_fits.json").read_text(encoding="utf-8"))["singles"]
        for view in views:
            group = [r for r in fitted if r["index"] == view["index"]]
            rate = sum(r["quality_passed"] for r in group) / len(group) if group else 0.
            if rate >= MIN_ACCEPTED_FRACTION:
                entries.append(dict(source=name, index=view["index"], camera=view["camera"], quality_rate=rate))
    return entries


def main():
    entries = collect()
    pairs = []
    for one, two in combinations(entries, 2):
        separation = angle(one["camera"], two["camera"])
        if separation >= MIN_ANGLE_DEG:
            pairs.append(dict(views=[{k: row[k] for k in ("source", "index", "quality_rate")}
                                    for row in (one, two)], angle_deg=separation))
    result = dict(eligible_views=len(entries), pairs=pairs, uses_truth=False,
                  minimum_quality_repeat_fraction=MIN_ACCEPTED_FRACTION,
                  minimum_separation_deg=MIN_ANGLE_DEG)
    (ROOT / "cross_batch_inventory.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
