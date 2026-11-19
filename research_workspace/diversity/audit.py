"""噪声和物理初态配对核验，不更改成功判据。"""
import json
import numpy as np
from reflection.reflector import Parameters
from flashnext.audit import audit_model
from stability.collection_worker import verify_pair
from diversity.worker import ROOT, ARMS
from diversity.config import scenario


def audit_records(result, task):
    config = scenario(task['seed'], task['level'])
    assert result['scenario'] == config and result['test_used'] is False
    assert result['scene_jitter_m'] == 0 and result['split'] == task['split']
    for key in ('source', 'destination', 'fault', 'seed'):
        assert result[key] == task[key]
    records = result['records']
    assert result['attempts'] == len(records) and 1 <= len(records) <= 3
    assert result['success'] == any(r['accepted'] for r in records)
    assert all(not r['accepted'] or r['physical_success'] for r in records)
    for index, record in enumerate(records):
        sensor = record['domain_randomization']['sensor_frames'][0]
        assert sensor['scene_seed'] == task['seed'] and sensor['attempt'] == index+1
        if task['level'] == 'clean':
            assert sensor['noisy_sha256'] == sensor['clean_sha256']
        else:
            assert sensor['noisy_sha256'] != sensor['clean_sha256']
        for field in ('initial_qpos', 'initial_body_xyz'):
            np.testing.assert_allclose(records[0]['candidate_trace'][field],
                                       record['candidate_trace'][field], atol=1e-8, rtol=0)
    for before, after in zip(records, records[1:]):
        parameters = Parameters().updated(before['parameters'])
        expected = parameters.updated(before.get('reflection', {}).get('changes', {}))
        assert expected == Parameters().updated(after['parameters'])


def audit_case(case, task):
    directory = ROOT/'tasks'/f'{case:02d}'
    results = {arm: json.loads((directory/arm/'result.json').read_text()) for arm in ARMS}
    for result in results.values():
        audit_records(result, task)
        verify_pair(result, results['retry'])
    first = [r['records'][0]['domain_randomization']['sensor_frames'][0] for r in results.values()]
    assert first[0] == first[1], 'Paired methods received different first depth observations'
    calls = audit_model(directory/'flash', results['flash'])
    return dict(case=case, passed=True, paired_noise_verified=True, model_calls=calls)


def summarize(rows):
    result = {}
    for level in ('clean', 'light', 'medium', 'strong'):
        result[level] = {}
        for arm in ARMS:
            selected = [r for r in rows if r['arm'] == arm and r['task']['level'] == level]
            result[level][arm] = dict(tasks=len(selected), successes=sum(r['success'] for r in selected),
                invalid=sum(r['invalid'] for r in selected), calls=sum(r['calls'] for r in selected))
    return result
