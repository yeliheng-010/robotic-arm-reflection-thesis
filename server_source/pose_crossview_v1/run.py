"""五个预登记跨批次组合，15次融合，拟合先于真值读取。"""
import os
from pathlib import Path
from pose_replay_v1.common import PROJECT, folders, identities, read, save, sha, load, truth_path
from pose_replay_v1.runtime import pair
from visibility_calibration_v1.analysis import accuracy, summary
from visibility_calibration_v1.policy import angle

ROOT = Path(__file__).resolve().parent
REPLAY = PROJECT / "pose_replay_v1"
REPEATS = range(3)


def input_identities():
    result = identities()
    paths = [REPLAY / f"{name}_fits.json" for name in sources()]
    paths.append(REPLAY / "audit.json")
    state_root = PROJECT / "held_observation_v3/trial/cases/964347/first/checkpoints/before_release"
    for name in ("state.npz", "snapshot.json"):
        path = state_root / name
        digests = []
        for package in ("visibility_calibration_v1", "visibility_boundary_v1", "visibility_boundary_v2"):
            manifest = PROJECT / package / "manifest.json"
            paths.append(manifest)
            digests.append(read(manifest)["identities"][str(path)])
        assert len(set(digests)) == 1 and sha(path) == digests[0]
        paths.append(path)
    result.update({str(p.relative_to(PROJECT)): sha(p) for p in paths})
    return result


def sources():
    return {name: folders()[name] for name in ("before_release", "boundary_v1", "boundary_v2")}


def cached(view, repeat):
    rows = read(REPLAY / f'{view["source"]}_fits.json')["singles"]
    return next(r for r in rows if r["index"] == view["index"] and r["repeat"] == repeat)


def verify_pair(views):
    cameras = []
    for view in views:
        folder = sources()[view["source"]]
        rows = read(folder / "views.json")
        cameras.append(next(r["camera"] for r in rows if r["index"] == view["index"]))
    measured = angle(*cameras)
    assert measured >= 10.
    return measured


def compute(views, repeat):
    clouds = [load(sources()[v["source"]], v["index"], repeat=repeat) for v in views]
    singles = [cached(v, repeat) for v in views]
    return pair(clouds, singles)


def main():
    assert read(REPLAY / "audit.json")["passed"]
    before = input_identities()
    for relative, digest in read(ROOT / "source_identities.json").items():
        assert sha(PROJECT / relative) == digest
    pairs = read(ROOT / "pairs.json")["pairs"]
    assert len(pairs) == 5
    save(ROOT / "started.json", dict(inputs=before, job_id=os.environ.get("SLURM_JOB_ID"),
         max_pairs=15, physical_attempts=0, model_calls=0, training_runs=0))
    results = []
    for index, selected in enumerate(pairs):
        separation = verify_pair(selected["views"])
        for repeat in REPEATS:
            results.append(dict(pair_index=index, views=selected["views"], repeat=repeat,
                angle_deg=separation, **compute(selected["views"], repeat)))
    save(ROOT / "fits.json", dict(rows=results, truth_used=False))
    truth = read(truth_path("before_release", sources()["before_release"]))
    rows = [dict(row, **accuracy(row["fit"], truth)) for row in results]
    save(ROOT / "private_errors.json", dict(rows=rows))
    save(ROOT / "analysis.json", dict(overall=summary(rows),
         pairs=[dict(index=i, **summary([r for r in rows if r["pair_index"] == i])) for i in range(5)],
         independent_layouts=1, deployed=False, release_authorized=False, training_eligible=False))
    assert input_identities() == before
    print(summary(rows), flush=True)


if __name__ == "__main__":
    main()
