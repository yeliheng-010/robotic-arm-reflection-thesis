import os
import argparse
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_session
from nc_observation import View
from top_session import StrategySession
from tp_common import ROOT, save, sha, verify, change, ACTIONS


def execute(case):
    folder = ROOT/'cases'/case['item']['id']
    folder.mkdir(parents=True, exist_ok=False)
    state, strategy = case['state'], 'original'
    steps, actions, observations = [], [], []
    for index in range(1,4):
        target = folder/f'attempt_{index}'
        configured = dict(case, control=dict(grasp_mode='world_down'), strategy=strategy)
        with patch.object(nc_session, 'Session', StrategySession):
            with nc_session.opened(configured, state, folder=target, index=index) as session:
                value = View(session, folder=target/'observations', remaining=0)
                path = target/'observation_summary.json'
                save(path, value.summary())
                observations.append(dict(path=str(path), sha256=sha(path)))
                steps.append(session.step)
        print(case['item']['id'], index, strategy, steps[-1]['success'], flush=True)
        if steps[-1]['success'] or index == 3:
            break
        action = ACTIONS[index-1]
        actions.append(dict(after_attempt=index, action=action))
        state, strategy = change(state, strategy, action=action)
    save(folder/'result.json', dict(status='completed', steps=steps, actions=actions, observations=observations,
        success=steps[-1]['success'], manifest_sha256=sha(ROOT/'manifest.json'), model_calls=0))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    parser = argparse.ArgumentParser()
    parser.add_argument('case_id')
    name = parser.parse_args().case_id
    case = next(c for c in verify()['cases'] if c['item']['id'] == name)
    execute(case)
    verify()


if __name__ == '__main__':
    main()
