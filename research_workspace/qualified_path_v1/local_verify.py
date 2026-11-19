"""本地纯数值复核；不声称重放MuJoCo物理检查。"""
import ast
import json
from collections import Counter
from pathlib import Path
import numpy as np
from model_grasp_intent_v1.geometry import propose
from qualified_model_v1.common import read, save, sha

PROJECT = Path(__file__).resolve().parent.parent
NUMERIC_ATOL = 1e-12  # Windows/Linux浮点库差异；不改变物理门槛。


def feedback():
    folder = PROJECT/'qualified_feedback_v1/evidence/remote/run'
    original = PROJECT/'qualified_intent_v1/evidence/remote/run/978505/observation.json'
    observation = read(original)
    rows = []
    for ordinal in (1, 2):
        decision = folder/f'decision_{ordinal}'
        action = read(decision/'validated.json')['action']
        rebuilt = propose(observation['target_points'], observation['nominal'], action)
        recorded = read(decision/'proposal.json')
        error = float(np.max(np.abs(np.asarray(recorded['pose'])-rebuilt['pose'])))
        np.testing.assert_allclose(recorded['pose'], rebuilt['pose'], atol=NUMERIC_ATOL, rtol=0)
        assert abs(recorded['required_width_m']-rebuilt['required_width_m']) <= NUMERIC_ATOL
        rows.append(dict(ordinal=ordinal, pose_numeric_match=True, max_component_error=error,
            width_m=rebuilt['required_width_m']))
    return rows


def delivery():
    count, sources = 0, 0
    for name in ('qualified_feedback_v1', 'qualified_path_v1'):
        for row in read(PROJECT/name/'evidence/DELIVERY.json')['files']:
            relative = row['path'].split('/', 1)[1]
            assert sha(PROJECT/name/'evidence/remote'/relative) == row['sha256']
            count += 1
            if '/' not in relative and Path(relative).suffix in ('.py', '.sh', '.sbatch', '.md'):
                assert sha(PROJECT/name/relative) == row['sha256']
                sources += 1
    return dict(transferred_text_files=count, source_files_identical=sources)


def main():
    verified = delivery()
    rows = feedback()
    result = read(PROJECT/'qualified_path_v1/evidence/remote/run/planning/978501/private_result.json')
    plan = result['plan']
    counts = dict(Counter(r['reason'] for r in plan['endpoints']['goals']))
    assert counts == dict(ik_failure=9, collision=9)
    assert not plan['prefixes'] and not plan['candidates'] and plan['selected'] is None
    assert result['strict']['passed'] is False
    files = [p for n in ('qualified_feedback_v1', 'qualified_path_v1') for p in (PROJECT/n).glob('*.py')]
    for path in files:
        text = path.read_text(encoding='utf-8')
        assert len(text.splitlines()) <= 300
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50
    save(PROJECT/'qualified_path_v1/LOCAL_VERIFICATION.json', dict(verified, numerical_rebuild=rows,
        release_failures=counts, parsed_files=len(files), local_mujoco_replay=False))
    print(json.dumps(dict(verified, numerical_rebuild=rows, release_failures=counts), ensure_ascii=False))


if __name__ == '__main__':
    main()
