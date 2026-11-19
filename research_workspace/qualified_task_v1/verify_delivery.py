"""本地只读核对传输、提示和纯数值抓姿，不声称重跑MuJoCo。"""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np
from model_grasp_intent_v1.geometry import propose
from model_grasp_intent_v1.model import parse

PROJECT = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def files():
    count, sources = 0, 0
    for package in ('qualified_task_v1', 'qualified_model_v1', 'qualified_intent_v1'):
        root = PROJECT/package
        for name, expected in read(root/'evidence/DELIVERY.json')['files'].items():
            raw = (root/'evidence/remote'/name).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == expected, name
            count += 1
            if '/' not in name and name.endswith(('.py', '.sbatch', '.md')):
                assert (root/name).read_bytes() == raw, name
                sources += 1
    return dict(transferred_text_files=count, source_files_identical=sources)


def numeric():
    evidence = PROJECT/'qualified_intent_v1/evidence/remote'
    rows = []
    for seed in (978501, 978505):
        raw = read(evidence/f'run/{seed}/observation.json')
        action = parse(read(evidence/f'run_v3/{seed}/response.json'))['action']
        result = propose(raw['target_points'], raw['nominal'], action)
        expected = read(evidence/f'run_v3/{seed}/proposal.json')
        assert result['status'] == expected['status'] == 'proposal'
        np.testing.assert_allclose(expected['pose'], result['pose'], atol=1e-12, rtol=0)
        np.testing.assert_allclose(expected['required_width_m'], result['required_width_m'], atol=1e-12, rtol=0)
        rows.append(dict(seed=seed, matched=True, target_points=len(raw['target_points']),
                         required_width_m=result['required_width_m']))
    return rows


def structure():
    count = 0
    for package in ('qualified_task_v1', 'qualified_model_v1', 'qualified_intent_v1'):
        for path in (PROJECT/package).glob('*.py'):
            text = path.read_text(encoding='utf-8')
            tree = ast.parse(text)
            assert len(text.splitlines()) <= 300, path
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    assert node.end_lineno-node.lineno+1 <= 50, (path, node.name)
                    assert len(node.args.posonlyargs+node.args.args) <= 3
            count += 1
    return count


if __name__ == '__main__':
    result = dict(files(), numerical_rebuild=numeric(), syntax_files=structure(),
                  local_mujoco_replay=False)
    with (PROJECT/'qualified_task_v1/LOCAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
