"""训练场景的遥测物理一致性检查；不读取测试任务。"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent
COLLECTION = ROOT.parent.parent / 'overnight_20261019/collection'
TRAIN_IDS = (16, 24, 32, 136, 144, 152)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='parity')
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    from reflection.__main__ import bootstrap
    bootstrap()
    import numpy as np
    from training.refine.engine import EvidenceEngine
    plan = json.loads((COLLECTION / 'plan.json').read_text())
    checks = []
    for index in TRAIN_IDS:
        task = plan[index]
        assert task['split'] == 'train'
        engine = EvidenceEngine(headless=True, task_parser='rule', scene_jitter=.012)
        directory = OUT / args.run / f'{index:05d}'
        try:
            saved = directory / 'result.json'
            if saved.exists():
                result = json.loads(saved.read_text())
            else:
                result = engine.run(**{k: v for k, v in task.items() if k != 'split'},
                                    method='baseline', output=directory, context='evidence-parity')
        finally:
            engine.close()
        original = json.loads((COLLECTION / 'tasks' / f'{index:05d}' / 'result.json').read_text())['records'][0]
        actual = json.loads(json.dumps(result['records'][0]))
        for key in ('error_type', 'message'):
            assert actual['error'][key] == original['error'][key]
        assert original['parameters'] == actual['parameters']
        assert original['physical_success'] == actual['physical_success']
        np.testing.assert_allclose(original['evaluation']['position'], actual['evaluation']['position'], atol=1e-8, rtol=0)
        diagnostics = actual['error']['evidence']['diagnostics']
        assert diagnostics['grasp_filter']['candidate_count'] >= 1
        if index == 24:
            assert diagnostics['motion_segment'] == 'transport'
            assert diagnostics['contact_bounds_world']
        if index == 144:
            assert diagnostics['grasp_filter']['surviving_count'] == 0
        if index in (32, 152) and args.run != 'parity':
            assert diagnostics['observation_phase'] == 'post_execution_evaluation'
            assert 'motion_segment' not in diagnostics
        checks.append(dict(case=f'{index:05d}', passed=True, diagnostics=diagnostics))
        print(json.dumps(checks[-1], ensure_ascii=False), flush=True)
    (OUT / (args.run + '.json')).write_text(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

