"""规则专家数据的独立统计、来源隔离、去重与数量门槛。"""
from collections import Counter
import json
from stability.collection_plan import LIMITS, MIN_PER_FAULT, FAULTS, HELDOUT
from stability.collection_status import atomic
from stability.expert_dataset import SOURCE


def datasets_from(summaries, *, stage):
    datasets, seen, duplicates = {s: [] for s in LIMITS}, {}, 0
    for summary in summaries:
        assert summary['supervision_source'] == SOURCE
        for row in summary['samples']:
            meta = row['metadata']
            assert meta['teacher_source'] == SOURCE and meta['model'] is None
            split, key = meta['split'], meta['prompt_sha256']
            if stage == 'batch':
                assert HELDOUT.get((meta['source'], meta['destination']), 'train') == split
            if key in seen:
                assert seen[key] == split, 'Cross-split prompt leakage'
                duplicates += 1
                continue
            seen[key] = split
            datasets[split].append(row)
    return datasets, duplicates


def update(directory, *, planned, stage):
    summaries = [json.loads(p.read_text()) for p in sorted((directory/'tasks').glob('*/summary.json'))]
    datasets, duplicates = datasets_from(summaries, stage=stage)
    (directory/'dataset').mkdir(exist_ok=True)
    for split, rows in datasets.items():
        target = directory/'dataset'/f'{split}.jsonl'
        temporary = target.with_suffix('.tmp')
        temporary.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))
        temporary.replace(target)
    coverage = {s: dict(Counter(r['metadata']['fault'] for r in rows)) for s, rows in datasets.items()}
    sufficient = (all(len(datasets[s]) >= count for s, count in LIMITS.items()) and
                  all(coverage['train'].get(f, 0) >= MIN_PER_FAULT for f in FAULTS))
    status = {'supervision_source': SOURCE, 'planned_tasks': planned, 'completed_tasks': len(summaries),
        'successful_expert_tasks': sum(s['expert_success'] for s in summaries),
        'samples': {s: len(rows) for s, rows in datasets.items()}, 'by_fault': coverage,
        'duplicate_inputs_excluded': duplicates, 'invalid': sum(s['invalid'] for s in summaries),
        'calls': sum(s['calls'] for s in summaries),
        'sample_count_gate': sufficient, 'training_started': False,
        'note': 'Programmatic expert labels; not pure LLM or human reasoning; final audit required'}
    atomic(directory/'status.json', status)
    return status
