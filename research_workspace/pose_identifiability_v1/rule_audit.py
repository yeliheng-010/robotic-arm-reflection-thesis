"""复用全部345次旧单视角估计，分来源/阶段评估联合规则。"""
import json
from pose_identifiability_v1.diagnose import PROJECT, ROOT, save, sha
from pose_identifiability_v1.rules import evaluate_rule
from visibility_calibration_v1.policy import THRESHOLDS


def sources():
    paths = {}
    for phase in ("preflight", "after_lift", "before_release"):
        paths[phase] = PROJECT / f"visibility_calibration_v1/evidence/remote/phases/{phase}/private_errors.json"
    for version in (1, 2):
        paths[f"before_release_boundary_v{version}"] = PROJECT / f"visibility_boundary_v{version}/evidence/remote/private_errors.json"
    return paths


def main():
    paths = sources()
    identities = {str(path.relative_to(PROJECT)): sha(path) for path in paths.values()}
    groups = {}
    for name, path in paths.items():
        rows = json.loads(path.read_text(encoding="utf-8"))["singles"]
        groups[name] = dict(observations=len(rows),
            all_quality=evaluate_rule(rows, 0.),
            thresholds=[dict(threshold=t, **evaluate_rule(rows, t)) for t in THRESHOLDS],
            full_frame_other_gates_accepted=sum(r["full_frame_other_gates"] for r in rows))
    assert sum(group["observations"] for group in groups.values()) == 345
    assert identities == {str(path.relative_to(PROJECT)): sha(path) for path in paths.values()}
    save(ROOT / "rule_audit.json", dict(groups=groups, identities=identities,
         independent_layouts=1, frozen_estimator_only=True, deployed=False,
         note="No cross-phase pooled accuracy; threshold scan is development only"))
    print(json.dumps({name: group["all_quality"] for name, group in groups.items()}))


if __name__ == "__main__":
    main()
