import os
import argparse
from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
from nc_audit_frames import view
from cp_audit import candidate_audit
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from sr_audit import measured
from top_audit import audit_attempt
from tp_common import ROOT, read, save, sha, verify, change, ACTIONS


def inspect(case):
    folder = ROOT/'cases'/case['item']['id']
    result = read(folder/'result.json')
    assert result['status'] == 'completed' and result['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert result['model_calls'] == 0 and 1 <= len(result['steps']) <= 3
    assert len(result['steps']) == len(result['observations']) == len(result['actions'])+1
    state, strategy, rows = case['state'], 'original', []
    for index, step in enumerate(result['steps'], 1):
        assert step['state'] == state and step['strategy'] == strategy and step['index'] == index
        assert step['control'] == dict(grasp_mode='world_down')
        with self_context(), joint_context(case['config']), mode(step['control']):
            record, geometry = audit_attempt(case, step)
        summary = view(result['observations'][index-1], case)
        assert len(summary['paths']) == 1 and summary['remaining'] == 0
        candidate_audit(step, case['config'])
        contacts = measured(Path(step['session_path']))
        assert contacts['self_contact_samples'] == 0
        save(Path(step['session_path'])/'contact_summary.json', contacts)
        rejected = (record.get('error') or {}).get('evidence',{}).get('route_planning_rejected',False)
        rows.append(dict(index=index, success=step['success'], strategy=strategy, route=geometry,
            planning_rejected=rejected, contacts={k:v for k,v in contacts.items() if k != 'closing_end'}))
        if index < len(result['steps']):
            assert not step['success']
            assert result['actions'][index-1] == dict(after_attempt=index, action=ACTIONS[index-1])
            state, strategy = change(state, strategy, action=ACTIONS[index-1])
    assert result['success'] == result['steps'][-1]['success']
    return dict(id=case['item']['id'], attempts=len(rows), success=result['success'], rows=rows)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    parser = argparse.ArgumentParser()
    parser.add_argument('--case-id', required=True)
    name = parser.parse_args().case_id
    case = next(c for c in verify()['cases'] if c['item']['id'] == name)
    row = inspect(case)
    files = [p for p in (ROOT/'cases'/name).rglob('*') if p.is_file()]
    save(ROOT/'audits'/(name+'.json'), dict(passed=True, row=row, training_ready=False,
        manifest_sha256=sha(ROOT/'manifest.json'), identities={str(p):sha(p) for p in files}))
    print(dict(id=name, attempts=row['attempts'], success=row['success']), flush=True)


if __name__ == '__main__':
    main()
