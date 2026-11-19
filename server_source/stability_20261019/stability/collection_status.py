"""有效样本、来源、分组泄漏与微调准备门槛。"""
from collections import Counter
import json
from stability.collection_plan import LIMITS, MIN_PER_FAULT, FAULTS


def atomic(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temporary.replace(path)


def update(directory, *, planned):
    summaries = [json.loads(p.read_text()) for p in sorted((directory/'tasks').glob('*/summary.json'))]
    datasets = {split: [] for split in LIMITS}
    seen, duplicates = {}, 0
    for summary in summaries:
        for row in summary['samples']:
            meta = row['metadata']
            split, key = meta['split'], meta['prompt_sha256']
            if key in seen:
                if seen[key] != split:
                    raise RuntimeError('Prompt leakage across splits')
                duplicates += 1
                continue
            seen[key] = split
            datasets[split].append(row)
    (directory/'dataset').mkdir(exist_ok=True)
    for split, rows in datasets.items():
        target = directory/'dataset'/f'{split}.jsonl'
        temporary = target.with_suffix('.tmp')
        temporary.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))
        temporary.replace(target)
    by_fault = {s: dict(Counter(r['metadata']['fault'] for r in rows)) for s, rows in datasets.items()}
    sufficient = (all(len(datasets[s]) >= count for s, count in LIMITS.items()) and
                  all(by_fault['train'].get(f, 0) >= MIN_PER_FAULT for f in FAULTS))
    status = {'planned_tasks': planned, 'completed_tasks': len(summaries),
        'successful_teacher_tasks': sum(s['teacher_success'] for s in summaries),
        'samples': {s: len(rows) for s, rows in datasets.items()}, 'by_fault': by_fault,
        'duplicate_inputs_excluded': duplicates, 'invalid': sum(s['invalid'] for s in summaries),
        'service_errors': sum(s['service_errors'] for s in summaries),
        'calls': sum(s['calls'] for s in summaries), 'sample_count_gate': sufficient,
        'training_started': False, 'note': 'Count gate alone is not complete data quality or efficacy evidence'}
    atomic(directory/'status.json', status)
    return status

