"""对相同资格观测使用实际顶面候选生成器；不执行物理动作。"""
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import span_qualify
from top_runtime import filter_context
from qualification_data import derive
from qual_one_v2 import reference
from qs_common import RUN, current, read, save, sha


def endpoints(plan):
    output = {}
    for stage in ('grasps', 'goals'):
        rows = plan['endpoints'][stage]
        counts = Counter('passed' if r['ok'] else r['reason'] for r in rows)
        pairs = Counter('|'.join(pair) for r in rows for pair in set(tuple(p) for p in r.get('contacts', [])))
        output[stage] = dict(total=len(rows), outcomes=dict(counts), contacts=dict(pairs))
    return output


def probe(row, *, output):
    case = row['case']
    folder = Path(row['qualification'])/'render'
    calibration = read(folder/'result.json')
    assert sha(folder/'sensor.npz') == calibration['sensor_sha256']
    projected, points, noise = derive(folder, case['config'], item=case['item'], calibration=calibration)
    assert projected == row['old']['projection'] and noise == row['old']['qualification_noise']
    assert len(points) == row['old']['points']
    with patch.object(span_qualify, 'ROOT', output), patch.object(span_qualify, 'span_context', filter_context):
        top = span_qualify.qualify(case, reference(), points)
    plan = read(top['path'])
    return dict(id=case['item']['id'], top=top, original=row['audit'], endpoints=endpoints(plan),
        same_qualification_observation=True, points=len(points), noise=noise,
        sensor_sha256=sha(folder/'sensor.npz'), physical_attempts=0, model_calls=0)


def main(name, mode):
    assert mode in ('probe', 'audit')
    row = current(name)
    output = RUN/mode/name
    output.mkdir(parents=True, exist_ok=False)
    result = probe(row, output=output)
    if mode == 'audit':
        saved = read(RUN/'probe'/name/'result.json')
        compare = lambda r: {k:v for k,v in r['top'].items() if k not in ('path', 'sha256')}
        assert compare(result) == compare(saved)
        assert read(result['top']['path']) == read(saved['top']['path'])
        assert result['sensor_sha256'] == saved['sensor_sha256']
        result['independently_reproduced'] = True
    paths = [Path(result['top']['path']), Path(row['qualification'])/'render/sensor.npz']
    result['identities'] = {str(p): sha(p) for p in paths}
    save(output/'result.json', result)
    print(dict(id=name, mode=mode, passed=result['top']['passed'], endpoints=result['endpoints'],
        fit=result['top']['span_filter'].get('observed_top_estimate')), flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
