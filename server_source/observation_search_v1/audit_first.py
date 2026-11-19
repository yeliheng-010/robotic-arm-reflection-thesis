from observation_search_v1.audit import layout
from observation_search_v1.common import RUN, SEEDS, verify, save


def main():
    manifest = verify()
    seed = SEEDS[0]
    result, errors, checks, rays = layout(seed, manifest['configs'][str(seed)])
    verify()
    save(RUN / 'first_audit.json', dict(passed=True, seed=seed, result=result, checks=checks,
        pose_errors=errors, ray_count=len(rays), gate_uses_qualification=False))
    print(dict(passed=True, seed=seed, ray_count=len(rays)), flush=True)


if __name__ == '__main__':
    main()
