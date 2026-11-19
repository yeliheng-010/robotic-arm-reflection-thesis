"""诊断与冻结三次预算基线配对，测量干预不混入动作或物理真值。"""
import numpy as np
from common import PREVIOUS, read, sha
from hardstudy.audit import clean_step
from hardstudy.feedback import project_step

PREFIX_FIELDS=('index','state','success','feedback','intervention_enabled','projection_seed','noise_audit')


def physical_equal(left,right):
    a=read(left['result_path'])['records'][0]
    b=read(right['result_path'])['records'][0]
    for field in ('initial_qpos','initial_body_xyz'):
        np.testing.assert_allclose(a['candidate_trace'][field],b['candidate_trace'][field],atol=1e-8,rtol=0)
    assert a['accepted']==b['accepted'] and a['physical_success']==b['physical_success']
    assert (a.get('error') or {}).get('error_type')==(b.get('error') or {}).get('error_type')
    np.testing.assert_allclose(a['evaluation']['position'],b['evaluation']['position'],atol=1e-8,rtol=0)


def prefix_equal(current,baseline):
    before=baseline['attempts']
    assert len(current['attempts'])>=len(before)
    for a,b in zip(before,current['attempts']):
        assert all(a[k]==b[k] for k in PREFIX_FIELDS), 'Original three-attempt prefix changed'
        physical_equal(a,b)
    for a,b in zip(baseline['decisions'],current['decisions']):
        for key in ('after_attempt','before','feedback','candidates','selected'):
            assert a[key]==b[key], 'Original decision prefix changed'
        if 'event' in a:
            assert a['event']['request']['messages']==b['event']['request']['messages']
            assert a['event'].get('text')==b['event'].get('text')
    return len(before)


def noise_checks(result,entry):
    paired,removed=0,0
    for step in result['attempts']:
        original=project_step(clean_step(step,entry['item']),entry['item'])
        assert original['projection_seed']==step['projection_seed']
        assert set(original['noise_audit'])==set(step['noise_audit'])
        for field,reference in original['noise_audit'].items():
            actual=step['noise_audit'][field]
            assert reference['original']==actual['original'] and reference['delta']==actual['delta']
            if entry['variant']=='no_missing':
                assert actual['missing'] is False
                removed+=int(reference['missing'])
            else:
                assert actual==reference
            paired+=1
    return paired,removed


def compare_baseline(result,entry):
    folder=PREVIOUS/'tasks'/entry['source_uid']
    baseline=read(folder/'result.json')
    summary=read(folder/'summary.json')
    assert sha(folder/'result.json')==summary['result_sha256']
    assert result['item']==baseline['item']
    physical_equal(baseline['attempts'][0],result['attempts'][0])
    prefix=prefix_equal(result,baseline) if entry['variant']=='budget4' else 0
    pairs,removed=noise_checks(result,entry)
    return dict(baseline_success=baseline['success'],prefix_checks=prefix,
        noise_delta_checks=pairs,masks_removed=removed,
        success_at_three=any(s['success'] for s in result['attempts'][:3]))
