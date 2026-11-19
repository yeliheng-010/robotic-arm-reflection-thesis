"""仅提取已使用的开发提示；不读取封存测试。"""
import json
from pathlib import Path
from refinement.config import ROOT, PROBES
from refinement.freeze import sha


def main():
    origin = Path('/home/yeliheng/grasp_server/controlled_v3/pilot/tasks')
    rows = []
    for case, attempt, label in PROBES:
        directory = origin/f'{case:02d}'/'flash'
        result = json.loads((directory/'result.json').read_text())
        events = [json.loads(x) for x in (directory/'requests.jsonl').read_text().splitlines()]
        feedback = [json.loads(x) for x in (directory/'feedback.jsonl').read_text().splitlines()]
        event, projection = events[attempt-1], feedback[attempt-1]
        rows.append(dict(case=case, attempt=attempt, label=label, instruction=result['instruction'],
                         parameters=result['records'][attempt-1]['parameters'],
                         report=projection['projected'], history=projection['history'],
                         original_request=event['request'],
                         source_hashes={str(p): sha(p) for p in directory.glob('*.json*')}))
    with (ROOT/'diagnostic_inputs.json').open('x') as stream:
        json.dump(rows, stream, ensure_ascii=False, indent=2)
    print('Prepared six archived diagnostic inputs')


if __name__ == '__main__':
    main()
