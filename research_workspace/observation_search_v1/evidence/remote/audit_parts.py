import os
from observation_search_v1.audit import layout
from observation_search_v1.common import ROOT, RUN, SEEDS, save, sha, verify

ADDITIONS = ('audit_parts.py', 'audit_merge.py', 'parts.sbatch', 'merge.sbatch', 'AUDIT_EXECUTION.md')


def main():
    manifest = verify()
    seed = SEEDS[int(os.environ['SLURM_ARRAY_TASK_ID'])]
    assert seed != SEEDS[0], 'First case already independently audited'
    sources = {str(ROOT / name): sha(ROOT / name) for name in ADDITIONS}
    save(RUN / f'audit_started_{seed}.json', dict(sources=sources, seed=seed,
        manifest_sha256=sha(RUN / 'manifest.json')))
    result, errors, checks, rays = layout(seed, manifest['configs'][str(seed)])
    verify()
    assert all(sha(path) == digest for path, digest in sources.items())
    save(RUN / f'audit_part_{seed}.json', dict(passed=True, seed=seed, result=result,
        pose_errors=errors, checks=checks, ray_count=len(rays), independent_process=True))
    print(dict(passed=True, seed=seed, ray_count=len(rays)), flush=True)


if __name__ == '__main__':
    main()
