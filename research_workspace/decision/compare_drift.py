"""不放宽容差，验证两种线程配置各自复现哪一批轨迹。"""
import json
import numpy as np
from decision.experiment import COLLECTION, OUT


def position(path):
    return np.array(json.loads(path.read_text())['records'][0]['evaluation']['position'])


def main():
    checks = []
    cases = [(32, '02', 'threads1', 'inherited'),
             (152, '05', 'cylinder_threads1', 'cylinder_inherited')]
    for original, case, single, inherited in cases:
        old = position(COLLECTION / 'tasks' / f'{original:05d}/result.json')
        current = position(OUT / 'train_v1' / case / 'hybrid/result.json')
        one = position(OUT / 'drift' / single / 'result.json')
        default = position(OUT / 'drift' / inherited / 'result.json')
        np.testing.assert_allclose(current, one, atol=1e-8, rtol=0)
        np.testing.assert_allclose(old, default, atol=1e-8, rtol=0)
        checks.append({'case': original, 'single_thread_matches_current': True,
                       'inherited_threads_match_original': True,
                       'between_profiles_max_difference_m': float(np.max(np.abs(old - current)))})
    output = {'status': 'passed', 'checks': checks,
              'interpretation': 'Thread profile changes reproduce both historical and current positions; do not claim cross-profile trajectory equality.'}
    (OUT / 'drift/comparison.json').write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
