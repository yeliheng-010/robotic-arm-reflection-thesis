"""用全部旧实验和本轮已生成结果回归审计器，避免只修单个例子。"""
import json
from pathlib import Path
from controlled.config import tasks
from controlled.audit import audit_records
from refinement.audit import audit_feedback, compare_saved, audit_run
from refinement.freeze import verify
from stability.collection_status import atomic


def main():
    verify()
    root = Path('/home/yeliheng/grasp_server/controlled_v3/pilot/tasks')
    total, calls = 0, 0
    for case, task in enumerate(tasks()):
        baseline = json.loads((root/f'{case:02d}'/'retry/result.json').read_text())
        for arm in ('retry', 'rule', 'flash'):
            directory = root/f'{case:02d}'/arm
            result = json.loads((directory/'result.json').read_text())
            # 重建 Python 原始接触元组和参数元组，复现落盘前的表示。
            for record in result['records']:
                for key in ('grasp_offset', 'place_offset'):
                    record['parameters'][key] = tuple(record['parameters'][key])
                evidence = (record.get('error') or {}).get('evidence', {})
                if 'contacts' in evidence:
                    evidence['contacts'] = [tuple(pair) for pair in evidence['contacts']]
            audit_records(result, task)
            compare_saved(result, baseline)
            calls += audit_feedback(directory, result, 'flash_old' if arm == 'flash' else 'rule_old')
            total += 1
    current = Path('/home/yeliheng/grasp_server/refinement_v2/smoke/tasks')
    for case, arm in ((22, 'rule_new'), (32, 'rule_old')):
        directory = current/f'{case:02d}_{arm}_0'
        result = json.loads((directory/'result.json').read_text())
        audit_run(directory, result, dict(case=case, arm=arm, repeat=0))
    value = dict(passed=True, historical_runs=total, historical_calls=calls, current_runs=2,
                 representation='reconstructed Python tuple parameters and contact pairs')
    atomic(Path('/home/yeliheng/grasp_server/refinement_v3/audit_regression.json'), value)
    print(json.dumps(value))


if __name__ == '__main__':
    main()

