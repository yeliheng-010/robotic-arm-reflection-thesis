"""新候选全量回放；原版结果直接读取，拟合时不读取真值。"""
import os
import platform
import scipy
import numpy as np
from pose_replay_v1.common import ROOT, PROJECT, folders, identities, read, save, sha, load
from pose_replay_v1.runtime import single, pair


def run_group(folder):
    previous = read(folder / "fits.json")
    singles, cached, pairs = [], {}, []
    for row in previous["singles"]:
        index, repeat = row["index"], row["repeat"]
        value = single(load(folder, index, repeat=repeat))
        cached[index, repeat] = value
        singles.append(dict(index=index, repeat=repeat, **value))
    for row in previous["pairs"]:
        indices, repeat = row["indices"], row["repeat"]
        clouds = [load(folder, index, repeat=repeat) for index in indices]
        value = pair(clouds, [cached[index, repeat] for index in indices])
        pairs.append(dict(indices=indices, repeat=repeat, **value))
    return dict(singles=singles, pairs=pairs)


def main():
    for relative, digest in read(ROOT / "source_identities.json").items():
        assert sha(PROJECT / relative) == digest, relative
    before = identities()
    save(ROOT / "started.json", dict(job_id=os.environ.get("SLURM_JOB_ID"), inputs=before,
         versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
         independent_layouts=1, physical_attempts=0, model_calls=0, training_runs=0))
    results = {}
    for name, folder in folders().items():
        results[name] = run_group(folder)
        save(ROOT / f"{name}_fits.json", results[name])
        print(dict(phase=name, singles=len(results[name]["singles"]),
                   pairs=len(results[name]["pairs"])), flush=True)
    assert sum(len(g["singles"]) for g in results.values()) == 345
    assert sum(len(g["pairs"]) for g in results.values()) == 132
    assert before == identities()
    save(ROOT / "fitted.json", dict(inputs_unchanged=True, single_count=345, pair_count=132))


if __name__ == "__main__":
    main()
