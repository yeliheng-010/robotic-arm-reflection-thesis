"""只读核验已完成批次：相机资格、拒绝分母和几何拒绝证据。"""
import os
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import span_qualify
from cv_select import scene, evaluate, image, PROPOSAL_BUDGET
from cv_entry import approved_config
from cv_policy import REQUIRED, frame_gate
from cv_rgb import compare_files
from sd_inventory import root_boxes
from qualification_data import derive
from qual_one_v2 import reference
from fa_common import RUN, SEEDS, read, save, sha, verify, base
from fa_result import totals

ROOT = Path(__file__).resolve().parent


def cameras(manifest, output):
    rows = []
    for seed in SEEDS:
        original = next(c['config'] for c in manifest['cases']
                        if c['item']['seed'] == seed and c['item']['group'] == 'varied_noisy')
        folder = RUN/'cameras'/str(seed)
        saved = read(folder/'selection.json')
        assert saved == read(RUN/'camera_results'/(str(seed)+'.json'))
        attempts = saved['attempts']
        assert [r['index'] for r in attempts] == list(range(len(attempts)))
        for row in attempts:
            if 'measurements' in row:
                assert frame_gate(row['measurements']) == row['gate']
        if not saved['accepted']:
            assert len(attempts) == PROPOSAL_BUDGET and not any(r['accepted'] for r in attempts)
            assert not (folder/'accepted_config.json').exists()
            rows.append(dict(seed=seed, accepted=False, rejection_preserved=True))
            continue
        config = approved_config(folder, original)
        with scene(config) as (env, renderer):
            boxes = root_boxes(env.mj_model, env.mj_data)
            actual = evaluate(env, renderer, config['camera'], boxes={n: boxes[n] for n in REQUIRED})
            assert actual['accepted'] and actual['measurements'] == attempts[-1]['measurements']
            path = output/(str(seed)+'.png')
            image(env, path)
            rgb = compare_files(folder/'after.png', path)
        rows.append(dict(seed=seed, accepted=True, candidates=len(attempts), rgb=rgb,
                         identical_metrics=True))
    return rows


def endpoint_summary(plan):
    result = {}
    for stage in ('grasps', 'goals'):
        rows = plan['endpoints'][stage]
        reasons = Counter('passed' if r['ok'] else r['reason'] for r in rows)
        pairs = Counter('|'.join(pair) for r in rows for pair in set(tuple(p) for p in r.get('contacts', [])))
        result[stage] = dict(total=len(rows), reasons=dict(reasons), contact_candidates=dict(pairs))
    return result


def geometry(row, output):
    folder = base(row['id'], 'original')
    case = verify(folder/'manifest.json')['cases'][0]
    source = folder/'qualification'/str(row['seed'])
    saved = read(source/'result.json')
    if 'geometry' not in saved:
        return dict(id=row['id'], status=saved['status'], replayed=False)
    render = source/'render'
    calibration = read(render/'result.json')
    assert sha(render/'sensor.npz') == calibration['sensor_sha256']
    _, points, noise = derive(render, case['config'], item=case['item'], calibration=calibration)
    assert noise == saved['qualification_noise']
    with patch.object(span_qualify, 'ROOT', output):
        actual = span_qualify.qualify(case, reference(), points)
    expected = saved['geometry']
    assert {k:v for k,v in actual.items() if k not in ('path', 'sha256')} == {
        k:v for k,v in expected.items() if k not in ('path', 'sha256')}
    plan = read(expected['path'])
    assert sha(expected['path']) == expected['sha256']
    assert plan == read(actual['path'])
    return dict(id=row['id'], status=actual['status'], replayed=True,
                endpoints=endpoint_summary(plan), accepted=actual['passed'])


def main():
    manifest, result = verify(RUN/'manifest.json'), verify(RUN/'result.json')
    assert result['complete'] and len(result['rows']) == 8
    assert result['totals'] == totals(result['rows'])
    assert result['physical_attempts'] <= manifest['max_attempts']
    output = ROOT/('job_'+os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=False)
    camera = cameras(manifest, output)
    geometries = [geometry(row, output) for row in result['rows']
                  if row['status'] not in ('camera_rejected', 'camera_unknown')]
    identities = dict(result['identities'])
    paths = [RUN/'result.json', Path(__file__), ROOT/'audit.sbatch']
    identities.update({str(p): sha(p) for p in paths})
    save(output/'result.json', dict(passed=True, camera=camera, geometry=geometries,
        totals=result['totals'], identities=identities, physical_attempts=0, model_calls=0))
    print(dict(passed=True, camera=camera, geometry=geometries), flush=True)


if __name__ == '__main__':
    main()
