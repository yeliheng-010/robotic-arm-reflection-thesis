"""只读提取冻结轨迹，重新审计，并保留原始文件指纹。"""
import copy
import hashlib
import json
from pathlib import Path
from refinement.freeze import verify
from refinement.audit import audit_run
from refinement.config import ROOT as SOURCE, runs, run_id
from controlled.config import tasks

ROOT = SOURCE.parent/'refinement_review_v1'
FILES = ('result.json', 'summary.json', 'feedback.jsonl', 'requests.jsonl')


def load(path, *, lines=False):
    if not path.exists():
        return [] if lines else None
    text = path.read_text()
    return [json.loads(x) for x in text.splitlines()] if lines else json.loads(text)


def compact(record):
    keys = ('attempt', 'accepted', 'physical_success', 'parameters', 'last_stage', 'reflection',
            'reflection_error', 'reflection_status', 'error', 'evaluation')
    value = copy.deepcopy({k: record.get(k) for k in keys})
    if value['error']:
        evidence = value['error'].get('evidence', {})
        evidence.get('diagnostics', {}).get('grasp_filter', {}).pop('collision_iou', None)
    return value


def read_run(directory):
    result = load(directory/'result.json')
    return dict(summary=load(directory/'summary.json'), instruction=result['instruction'],
                scenario=result.get('scenario'), records=[compact(r) for r in result['records']],
                events=load(directory/'requests.jsonl', lines=True),
                feedback=load(directory/'feedback.jsonl', lines=True),
                source_files={str(directory/name): hashlib.sha256((directory/name).read_bytes()).hexdigest()
                              for name in FILES if (directory/name).exists()})


def main():
    protocol = verify()
    final = load(SOURCE/'regression/result.json')
    assert final['status'] == 'completed' and final['completed'] == final['expected'] == 96
    assert final['verification_passed']
    rows, audits = [], []
    for item in runs('regression'):
        directory = SOURCE/'regression/tasks'/run_id(item)
        result = load(directory/'result.json')
        audits.append(dict(**item, **audit_run(directory, result, item)))
        row = read_run(directory)
        saved = next(r for r in final['rows'] if all(r[k] == v for k, v in item.items()))
        assert all(saved[k] == v for k, v in row['summary'].items())
        assert saved['parsed_model_calls'] == sum('parsed' in e for e in row['events'])
        rows.append(dict(id=run_id(item), **item, **row))
    controls = {}
    for case in sorted({r['case'] for r in rows}):
        directory = SOURCE.parent/'controlled_v3/pilot/tasks'/f'{case:02d}'/'retry'
        controls[str(case)] = read_run(directory)
    data = dict(runs=rows, controls=controls, tasks=tasks(), final_metrics=final['metrics'],
                frozen_new_files=len(protocol['code']), audits=audits, test_used=False,
                scope='selected development conditions; repeated runs are not independent scenes')
    ROOT.mkdir(exist_ok=True)
    with (ROOT/'review_data.json').open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
    print(json.dumps(dict(runs=len(rows), controls=len(controls), audits=len(audits),
                          new_flash_failures=sum(r['arm']=='flash_new' and not r['summary']['success'] for r in rows))))


if __name__ == '__main__':
    main()
