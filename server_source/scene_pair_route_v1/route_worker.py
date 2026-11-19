"""最多三次，第一次共享；无认证路径立即结束，不绕过保护。"""
import os
from sd_common import read, save, sha
from cp_worker import bound
from depth_runtime import context as depth_context
from candidate_runtime import context as candidate_context
from loopstudy import episode
import sd_physics
from rc_policy import decide
from contact_capture import capture
from guard_scope import context as guard_context
from route_runtime import context as route_context
from route_policy import eligible
from route_inputs import ROOT
from route_prepare import verify


def execute(case, previous, *, index, folder, excluded, state):
    item, config = case['item'], case['config']
    trace, guard = {}, {}
    folder.mkdir(parents=True, exist_ok=False)
    active = eligible(previous['feedback'], item['destination'])
    with capture(folder/'contacts.jsonl', item), bound(config), depth_context(), \
         candidate_context(config), guard_context(item, guard), \
         route_context(item, state, trace, feedback=previous['feedback'], excluded=excluded):
        if active or index == 2:
            step = episode.attempt(item, state, directory=folder/'execution', index=index)
        else:
            step = sd_physics.motion_attempt(item, state, directory=folder/'execution',
                                            policy='geometry', feedback=previous['feedback'])
    save(folder/'route.json', trace)
    save(folder/'guard.json', guard)
    save(folder/'audit.json', dict(step=step, route_sha256=sha(folder/'route.json'),
         guard_sha256=sha(folder/'guard.json'), trace_sha256=sha(folder/'contacts.jsonl')))
    print(case['id'], index, 'success', step['success'],
          'route', (trace.get('selected') or {}).get('id'), flush=True)
    return step, trace


def run(case):
    folder = ROOT/'physics'/case['id']
    folder.mkdir(parents=True, exist_ok=False)
    steps, decisions, excluded = [case['first']], [], set()
    state = steps[-1]['state']
    for index in (2, 3):
        if not eligible(steps[-1]['feedback'], case['item']['destination']):
            decision = decide(steps, decisions, method='rule')
            decisions.append(decision)
            if decision['selected'] is None:
                break
            state = decision['selected']['state']
        step, trace = execute(case, steps[-1], index=index, folder=folder/f'attempt_{index}',
                              excluded=excluded, state=state)
        steps.append(step)
        save(folder/'progress.json', dict(steps=steps, decisions=decisions))
        if trace.get('selected'):
            excluded.add(trace['selected']['id'])
        rejected = trace['active'] and trace.get('selected') is None
        if step['success'] or rejected:
            break
    save(folder/'result.json', dict(item=case['item'], steps=steps, decisions=decisions,
         success=steps[-1]['success'], shared_first=True, new_attempts=len(steps)-1,
         excluded=sorted(excluded), manifest_sha256=sha(ROOT/'manifest.json')))


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    for case in manifest['cases']:
        if not case['reused_success']:
            run(case)
    verify()
    save(ROOT/'run_complete.json', dict(complete=True, manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
