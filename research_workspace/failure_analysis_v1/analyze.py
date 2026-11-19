"""只读复核闭环记录，统计同输入动作分歧与训练监督覆盖。"""
import json
from collections import Counter
from pathlib import Path

from common import ROOT as SOURCE, read, save, sha, verify
from audit_task import audit
from loopstudy.selection import messages

ROOT = SOURCE.parent / 'failure_analysis_v1'
METHODS = ('rule', 'base', 'tuned')


def input_for(result, offset):
    decision = result['decisions'][offset]
    return messages(decision['feedback'], decision['before'],
                    rows=decision['candidates'], history=result['decisions'][:offset])


def action(decision):
    selected = decision['selected']
    if selected is None:
        return None
    return {key: selected[key] for key in ('id', 'kind', 'changes', 'state')}


def compact(result):
    attempts = []
    for step in result['attempts']:
        feedback = step['feedback'] or {}
        evidence = feedback.get('evidence', {})
        attempts.append(dict(index=step['index'], success=step['success'],
            error=feedback.get('error_type'), phase=evidence.get('motion_context', {}).get('phase'),
            state=step['state'], grasp=evidence.get('grasp_residual_xy'),
            place=evidence.get('placement_residual_xy'), noise_audit=step.get('noise_audit'),
            result_path=step['result_path'], result_sha256=step['result_sha256']))
    return dict(success=result['success'], attempts=attempts,
                decisions=[action(d) for d in result['decisions']])


def compare(left, right):
    counts = Counter()
    differences = []
    for offset in range(min(len(left['decisions']), len(right['decisions']))):
        same = input_for(left, offset) == input_for(right, offset)
        a, b = action(left['decisions'][offset]), action(right['decisions'][offset])
        counts['same_input' if same else 'different_input'] += 1
        if same:
            counts['same_choice' if a == b else 'different_choice'] += 1
        if a != b:
            differences.append(dict(after_attempt=offset+1, same_input=same, left=a, right=b))
    return dict(counts=counts, differences=differences)


def training_coverage():
    path = SOURCE.parent / 'data_review_v1/output_v1/train_combined.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    kinds, phases, missing = Counter(), Counter(), Counter()
    for row in rows:
        prompt = json.loads(next(m['content'] for m in row['messages'] if m['role'] == 'user'))
        target = json.loads(row['messages'][-1]['content'])['action_id']
        candidate = next(c for c in prompt['candidates'] if c['id'] == target)
        kind = candidate['kind']
        if kind == 'descent_route':
            kind += ':' + candidate['state']['profile']
        kinds[kind] += 1
        evidence = prompt['error']['evidence']
        phases[evidence.get('motion_context', {}).get('phase', 'unknown')] += 1
        if not any(k in evidence for k in ('grasp_residual_xy', 'placement_residual_xy')):
            missing[kind] += 1
    return dict(samples=len(rows), kinds=kinds, phases=phases,
                no_visible_residual=missing, path=str(path), sha256=sha(path))


def main():
    manifest = verify()
    verification = read(SOURCE / 'verification.json')
    assert verification['passed'] and verification['complete']
    rows = {row['uid']: row for row in verification['rows']}
    grouped, identities = {}, {}
    for entry in manifest['entries']:
        path = SOURCE / 'tasks' / entry['uid'] / 'result.json'
        result = read(path)
        assert sha(path) == rows[entry['uid']]['result_sha256']
        assert audit(result, entry) == rows[entry['uid']]['audit']
        grouped.setdefault(entry['item']['scene_id'], {})[entry['method']] = result
        identities[str(path)] = sha(path)
    cases, comparisons = [], {}
    for scene, group in grouped.items():
        assert set(group) == set(METHODS)
        detail = {}
        for left, right in (('base', 'tuned'), ('rule', 'base'), ('rule', 'tuned')):
            key = left + '_vs_' + right
            value = compare(group[left], group[right])
            comparisons.setdefault(key, Counter()).update(value['counts'])
            if value['differences']:
                detail[key] = value['differences']
        if detail or any(not r['success'] for r in group.values()):
            cases.append(dict(scene=scene, methods={k: compact(v) for k, v in group.items()},
                              differences=detail))
    failed_scenes = [s for s, g in grouped.items() if any(not r['success'] for r in g.values())]
    summary = dict(passed=True, audited_tasks=len(rows), conditions=len(grouped),
        failed_tasks=sum(not r['success'] for r in rows.values()), failed_scenes=failed_scenes,
        comparisons=comparisons, training_coverage=training_coverage(),
        manifest_sha256=sha(SOURCE/'manifest.json'), verification_sha256=sha(SOURCE/'verification.json'),
        test_used=False, new_training_samples=0, physical_reruns=0)
    assert summary['audited_tasks'] == 180 and summary['conditions'] == 60
    assert summary['training_coverage']['samples'] == 159
    save(ROOT/'source_hashes.json', identities)
    save(ROOT/'cases.json', cases)
    save(ROOT/'summary.json', summary)
    assert all(sha(Path(p)) == value for p, value in identities.items())
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
