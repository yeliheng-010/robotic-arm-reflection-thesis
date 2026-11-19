"""Rebuild grouped, prompt-disjoint datasets from physical task records."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import time


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def split_examples(rows):
    """Keep seed groups intact; reserve held-out prompts before accepting train rows.

    Even if answers differ, identical system/user prompts cannot cross splits.
    The same system/user prompt is retained only once within each split.
    """
    output = {'train': [], 'validation': [], 'test': []}
    seen = set()
    dropped = Counter()
    for split in ('test', 'validation', 'train'):
        for row in rows:
            if row['metadata']['split'] != split:
                continue
            key = digest(row['messages'][:2])
            if key in seen:
                dropped[split] += 1
                continue
            seen.add(key)
            row['metadata']['prompt_sha256'] = key
            row['metadata']['sample_sha256'] = digest(row['messages'])
            output[split].append(row)
    return output, dict(dropped)


def finalize(output, stop_reason=None):
    from training.qlora import data
    from training.overnight.prompt import SYSTEM, FORMAT
    data.SYSTEM = SYSTEM
    from training.qlora.export_verified import verified_examples
    output = Path(output)
    status_path = output/'status.json'
    previous = json.loads(status_path.read_text()) if status_path.exists() else {}
    if stop_reason in ('collector_exited', 'scheduler_collection_ended') and previous.get('stop_reason') not in (None, 'in_progress'):
        stop_reason = previous['stop_reason']
    manifest = json.loads((output/'manifest.json').read_text())
    plan = json.loads((output/'plan.json').read_text())
    rows, results, errors = [], [], []
    for index, task in enumerate(plan):
        directory = output/'tasks'/f'{index:05d}'
        path = directory/'result.json'
        if not path.exists():
            if (directory/'error.json').exists():
                errors.append({'index': index, **json.loads((directory/'error.json').read_text())})
            continue
        result = json.loads(path.read_text())
        # Export only results matching the frozen task plan.
        if any(result.get(k) != task[k] for k in ('seed', 'source', 'destination', 'fault', 'instruction')):
            raise ValueError(f'Task result does not match plan: {path}')
        results.append(result)
        for row in verified_examples(result, path.relative_to(output)):
            row['metadata'].update(
                split=task['split'], teacher_model=manifest['teacher']['model'],
                prompt_format=FORMAT, result_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                persistent_fault=result['persistent_fault'],
            )
            rows.append(row)
    splits, dropped = split_examples(rows)
    dataset = output/'dataset'
    dataset.mkdir(exist_ok=True)
    hashes = {}
    for split, examples in splits.items():
        path = dataset/f'{split}.jsonl'
        text = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in examples)
        temp = path.with_suffix('.jsonl.tmp')
        temp.write_text(text)
        temp.replace(path)
        hashes[split] = hashlib.sha256(path.read_bytes()).hexdigest()
    counts = {k: len(v) for k, v in splits.items()}
    train_faults = Counter(row['metadata']['fault'] for row in splits['train'])
    persistent_types = set(train_faults) & {'calibration', 'collision', 'placement'}
    ready = (counts['train'] >= 100 and counts['validation'] >= 10 and counts['test'] >= 10
             and len(train_faults) >= 3 and len(persistent_types) >= 2)
    report = {
        'planned_tasks': len(plan), 'completed_tasks': len(results), 'task_errors': len(errors),
        'successful_tasks': sum(r['success'] for r in results),
        'reflection_calls': sum('reflection' in rec for r in results for rec in r['records']),
        'invalid_reflections': sum('reflection_error' in rec for r in results for rec in r['records']),
        'verified_before_prompt_dedup': len(rows), 'samples': counts,
        'verified_by_fault': {k: dict(Counter(x['metadata']['fault'] for x in v)) for k, v in splits.items()},
        'prompt_duplicates_dropped': dropped, 'dataset_sha256': hashes,
        'seed_groups': {split: sorted({t['seed'] for t in plan if t['split'] == split}) for split in splits},
        'teacher_model': manifest['teacher']['model'], 'prompt_format': FORMAT,
        'updated_utc_epoch': time.time(), 'deadline_utc_epoch': manifest['config']['deadline'],
        'stop_reason': stop_reason or 'in_progress',
        'ready_for_initial_training': ready,
        'readiness_rule': '>=100 train, >=10 validation, >=10 test; >=3 train fault types including >=2 persistent types. Starting criterion, not sufficiency proof.',
        'limitations': [
            'Simulation perception and geometric grasp; text-only reflection, not visual-language training.',
            'Immediate next-attempt success is selection evidence, not proof of causal benefit.',
            'Planning and grounding injections disappear after attempt 1; retry controls are required for causal claims.',
            'Seed-held-out sets share objects and scene; separate harder external evaluation is still needed.',
        ],
    }
    atomic(output/'status.json', report)
    atomic(dataset/'manifest.json', report)
    atomic(output/'task_errors.json', errors)
    message = '达到初步训练启动门槛' if ready else '尚未达到初步训练启动门槛，需补样本或检查失败原因'
    (output/'MORNING_REPORT.md').write_text(
        '# 夜间样本报告\n\n' + message + '。此门槛不代表模型效果已经验证。\n\n'
        + f"已完成 {len(results)}/{len(plan)} 个物理仿真任务，异常 {len(errors)} 个。\n\n"
        + f"去重后 train={counts['train']}，validation={counts['validation']}，test={counts['test']}。\n\n"
        + '状态及分故障统计见 status.json；数据位于 dataset/。按场景种子预分组，三个集合之间无重复输入提示。\n\n'
        + 'planning/grounding 故障第二次尝试会自然消失；必须另做无反思重试对照，不能用这些成功直接证明反思有效。\n\n'
        + '今晚只采集和整理数据，不自动启动正式训练。\n'
    )
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stop-reason', default='job_finished_or_interrupted')
    args = parser.parse_args()
    print(json.dumps(finalize(args.output, args.stop_reason), ensure_ascii=False, indent=2))
