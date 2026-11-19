"""每个静态有路的任务只新增第三次，其他任务不启动环境。"""
import os
from sd_common import read, save, sha
from cp_worker import bound
from depth_runtime import context as depth_context
from candidate_runtime import context as candidate_context
from loopstudy import episode
from contact_capture import capture
from guard_scope import context as guard_context
from waypoint_runtime import context as route_context
from waypoint_inputs import ROOT
from waypoint_prepare import verify


def run(case):
    folder = ROOT/'physics'/case['id']
    folder.mkdir(parents=True, exist_ok=False)
    prior = case['steps'][-1]
    assert prior['index'] == 2
    record = read(prior['result_path'])['records'][0]
    previous_trace = read(case['prior_trace'])
    trace, guard = {}, {}
    with capture(folder/'contacts.jsonl', case['item']), bound(case['config']), depth_context(), \
         candidate_context(case['config']), guard_context(case['item'], guard), \
         route_context(case['item'], prior['state'], trace, previous_record=record, previous_trace=previous_trace):
        step = episode.attempt(case['item'], prior['state'], directory=folder/'attempt_3', index=3)
    save(folder/'route.json', trace)
    save(folder/'guard.json', guard)
    save(folder/'result.json', dict(item=case['item'], steps=case['steps']+[step], success=step['success'],
         new_attempts=1, manifest_sha256=sha(ROOT/'manifest.json'),
         route_sha256=sha(folder/'route.json'), guard_sha256=sha(folder/'guard.json'),
         trace_sha256=sha(folder/'contacts.jsonl')))
    print(case['id'], 'success', step['success'], 'selected', (trace.get('selected') or {}).get('id'), flush=True)


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    for case in manifest['cases']:
        if case['id'] in manifest['selected']:
            run(case)
    verify()
    save(ROOT/'run_complete.json', dict(complete=True, actual_new_attempts=len(manifest['selected']),
                                       manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
