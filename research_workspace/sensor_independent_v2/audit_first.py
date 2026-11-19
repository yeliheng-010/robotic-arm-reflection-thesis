"""只验证首个预登记布局的工程完整性，不以资格结果决定是否扩批。"""
from sensor_independent_v2.audit import layout
from sensor_independent_v2.common import RUN, SEEDS, verify, save


def main():
    manifest = verify()
    seed = SEEDS[0]
    result, errors, checks, rays = layout(seed, manifest['configs'][str(seed)])
    verify()
    save(RUN / 'first_audit.json', dict(passed=True, seed=seed, result=result, checks=checks,
        pose_errors=errors, ray_count=len(rays), gate_uses_qualification=False,
        meaning='Engineering integrity only; no efficacy selection'))
    print(dict(passed=True, seed=seed, ray_count=len(rays)), flush=True)


if __name__ == '__main__':
    main()
