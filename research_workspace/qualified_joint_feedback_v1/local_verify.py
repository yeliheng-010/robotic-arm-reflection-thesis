"""本地复核公开输入、模型姿态、传输哈希与统计，不替代MuJoCo审计。"""
import ast
import json
from pathlib import Path
import numpy as np
from qualified_model_v1.common import read, save, sha
from model_grasp_intent_v1.geometry import propose
from qualified_joint_feedback_v1 import policy

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def delivery():
    count, sources = 0, 0
    for name in ('qualified_joint_feedback_v1', 'qualified_entry_v1'):
        for entry in read(PROJECT/name/'evidence/DELIVERY.json')['files']:
            relative = entry['path'].split('/', 1)[1]
            assert sha(PROJECT/name/'evidence/remote'/relative) == entry['sha256']
            count += 1
            if '/' not in relative and Path(relative).suffix in ('.py', '.sh', '.sbatch', '.md'):
                assert sha(PROJECT/name/relative) == entry['sha256']
                sources += 1
    return dict(text_files=count, sources_identical=sources)


def verify_row(row):
    seed, ordinal = row['seed'], row['ordinal']
    folder = ROOT/f'evidence/remote/run/{seed}/decision_{ordinal}'
    previous = PROJECT/f'qualified_intent_v1/evidence/remote/run_v3/{seed}/request.json'
    before, after = [json.loads(read(p)['messages'][1]['content']) for p in (previous, folder/'request.json')]
    assert before['observation'] == after['observation'] and before['actions'] == after['actions']
    geometry = read(PROJECT/f'qualified_path_v1/evidence/remote/run/goals/{seed}/geometry.json')
    assert after['observed_placement'] == {k: policy.compact(geometry[k]) for k in policy.GEOMETRY_KEYS}
    action = read(folder/'validated.json')['action']
    observation = read(PROJECT/f'qualified_intent_v1/evidence/remote/run/{seed}/observation.json')
    rebuilt = propose(observation['target_points'], observation['nominal'], action)
    recorded = read(folder/'proposal.json')
    np.testing.assert_allclose(recorded['pose'], rebuilt['pose'], atol=1e-12, rtol=0)
    assert abs(recorded['required_width_m']-rebuilt['required_width_m']) <= 1e-12
    plan = read(folder/'private_plan.json')
    assert read(folder/'result.json') == policy.outcome(plan)
    endpoints = plan['plan']['endpoints']
    return dict(seed=seed, ordinal=ordinal, pose_numeric_match=True,
        grasp_passing=sum(r['ok'] for r in endpoints['grasps']), release_passing=endpoints['passing'],
        release_total=len(endpoints['goals']), static_passed=plan['strict']['passed'])


def main():
    verified = delivery()
    records = read(ROOT/'evidence/remote/run/result.json')['rows']
    rows = [verify_row(row) for row in records]
    files = [p for n in ('qualified_joint_feedback_v1', 'qualified_entry_v1') for p in (PROJECT/n).glob('*.py')]
    for path in files:
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= 300
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno-node.lineno+1 <= 50 and len(node.args.args) <= 3
    result = dict(verified, rows=rows, parsed_files=len(files), local_mujoco_replay=False,
        physical_attempts=0, training_runs=0)
    save(ROOT/'LOCAL_VERIFICATION.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
