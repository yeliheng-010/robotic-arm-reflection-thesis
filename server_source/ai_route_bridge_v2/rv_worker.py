import argparse
import os
from unittest.mock import patch
from rv_common import ROOT, save, sha, verify, change
import nc_session
from nc_observation import View
from rv_runtime import VerticalSession


def execute(case):
    folder = ROOT/'cases'/case['item']['id']
    folder.mkdir(parents=True, exist_ok=False)
    if not case['config']['geometry_accepted'] or not case['config']['compiled_check']['passed']:
        save(folder/'result.json', dict(status='geometry_rejected', steps=[], actions=[], observations=[]))
        return
    state, control = case['state'], dict(grasp_mode='original')
    steps, actions, observations = [], [], []
    for index in range(1, 4):
        target = folder/f'attempt_{index}'
        with patch.object(nc_session, 'Session', VerticalSession):
            with nc_session.opened(dict(case, control=control), state, folder=target, index=index) as session:
                value = View(session, folder=target/'observations', remaining=0)
                path = target/'observation_summary.json'
                save(path, value.summary())
                observations.append(dict(path=str(path), sha256=sha(path)))
                steps.append(session.step)
        print(case['item']['id'], index, steps[-1]['success'], flush=True)
        if steps[-1]['success'] or index == 3:
            break
        action = 'SAFE_ROUTE' if index == 1 else 'WORLD_DOWN_ROUTE'
        actions.append(dict(after_attempt=index, action=action))
        state, control = change(state, control, action=action)
    save(folder/'result.json', dict(status='completed', steps=steps, actions=actions, observations=observations,
        success=steps[-1]['success'], manifest_sha256=sha(ROOT/'manifest.json'), model_calls=0))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    parser = argparse.ArgumentParser()
    parser.add_argument('case_id')
    args = parser.parse_args()
    manifest = verify()
    execute(next(c for c in manifest['cases'] if c['item']['id']==args.case_id))
    verify()


if __name__ == '__main__':
    main()
