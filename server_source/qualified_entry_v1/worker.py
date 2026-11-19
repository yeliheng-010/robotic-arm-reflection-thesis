from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from qualified_joint_feedback_v1.common import verify as parent
from qualified_model_v1.common import read, save, sha
from qualified_path_v1 import planning
from qualified_path_v1.worker import inspect
from qualified_entry_v1 import commands, held_preview

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT/'run'
SEED = 978505


def registration():
    identities = dict(parent()['identities'])
    source = PROJECT/'qualified_joint_feedback_v1/run'
    audit = read(source/'audit_result.json')
    assert audit['passed']
    assert read(source/'result.json')['ready_layouts'] == [SEED]
    identities.update(audit['identities'])
    paths = [source/'audit_result.json', *[p for p in ROOT.iterdir() if p.is_file()]]
    identities.update({str(p): sha(p) for p in paths})
    assert all(sha(p) == h for p, h in identities.items())
    save(RUN/'manifest.json', dict(identities=identities, seed=SEED,
        max_task_attempts=0, max_model_calls=0, max_training_runs=0,
        scope='Native command equivalence and private predicted held-observation preflight'))


def main():
    registration()
    source = PROJECT/f'qualified_joint_feedback_v1/run/{SEED}/decision_1'
    record = read(source/'private_plan.json')
    case = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases'][str(SEED)]
    def replay(flow, case, *, geometry, proposal):
        command = commands.run(flow, case, plan=record['plan'], folder=RUN)
        save(RUN/'commands.json', command)
        forecast = held_preview.inspect(flow, case, plan=record['plan'], folder=RUN/'predicted_held')
        save(RUN/'held_preview.json', forecast)
        return dict(commands_passed=command['passed'], predicted_held_qualified=forecast['accepted'],
            physical_attempts=0, actual_held_verified=False, execution_authorized=False)
    with patch.object(planning, 'run', replay):
        result = inspect(case, read(source/'proposal.json'),
            geometry=read(PROJECT/f'qualified_path_v1/run/goals/{SEED}/geometry.json'))
    assert all(sha(p) == h for p, h in read(RUN/'manifest.json')['identities'].items())
    save(RUN/'result.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
