"""从已完成实验提取可追溯复盘证据，不修改实验代码和结果。"""
import copy
import hashlib
import json
from pathlib import Path

SOURCE = Path('/home/yeliheng/grasp_server/controlled_v3')
OUTPUT = Path('/home/yeliheng/grasp_server/controlled_review_v1')
ARMS = ('retry', 'rule', 'flash')


def load(path, *, lines=False):
    if not path.exists():
        return [] if lines else None
    content = path.read_text()
    return [json.loads(s) for s in content.splitlines()] if lines else json.loads(content)


def compact_error(value):
    if value is None:
        return None
    result = copy.deepcopy(value)
    result.pop('image_paths', None)
    filtering = result.get('evidence', {}).get('diagnostics', {}).get('grasp_filter', {})
    filtering.pop('collision_iou', None)
    return result


def read_arm(directory):
    result = load(directory/'result.json')
    events = load(directory/'requests.jsonl', lines=True)
    feedback = load(directory/'feedback.jsonl', lines=True)
    records = []
    for record in result['records']:
        row = {key: record.get(key) for key in ('attempt', 'accepted', 'physical_success', 'parameters',
                'last_stage', 'reflection', 'reflection_error', 'reflection_status')}
        row['error'] = compact_error(record['error'])
        row['evaluation'] = {k: v for k, v in record.get('evaluation', {}).items()
                             if k not in ('diagnostics', 'depth_sensor')}
        records.append(row)
    return dict(summary=load(directory/'summary.json'), records=records, events=events, feedback=feedback,
                source_files={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (directory/'result.json', directory/'requests.jsonl', directory/'feedback.jsonl')
                              if p.exists()})


def main():
    final = load(SOURCE/'pilot/result.json')
    assert final['status'] == 'completed' and final['completed'] == final['expected'] == 144
    assert final['verification_passed'] and len(final['audits']) == 48
    protocol = load(SOURCE/'protocol.json')
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha for p, sha in protocol['code'].items())
    cases = []
    for case, task in enumerate(protocol['tasks']):
        directory = SOURCE/'pilot/tasks'/f'{case:02d}'
        cases.append(dict(case=case, task=task, arms={arm: read_arm(directory/arm) for arm in ARMS}))
    result = dict(source=str(SOURCE), task_count=len(cases), cases=cases,
                  frozen_files_verified=len(protocol['code']), test_used=False)
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT/'review_data.json').open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(dict(cases=len(cases), bytes=(OUTPUT/'review_data.json').stat().st_size,
                          path=str(OUTPUT/'review_data.json'))))


if __name__ == '__main__':
    main()
