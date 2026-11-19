"""补充多有效标签与真实 motion_context 分析，不修改导出快照。"""
import json
from collections import Counter, defaultdict
from pathlib import Path
from verify_output import OUTPUT, HERE, lines, file_hash


def motion_phase(feedback):
    return (feedback or {}).get('evidence',{}).get('motion_context',{}).get('phase')


def ambiguous(records):
    quarantined = {r['uid'] for r in lines(OUTPUT/'quarantine.jsonl')}
    groups = defaultdict(list)
    for row in records:
        if row['uid'] in quarantined:
            groups[row['input_hash']].append(row)
    output = []
    for key, members in sorted(groups.items()):
        visible = json.loads(members[0]['messages'][1]['content'])
        targets = {r['target'] for r in members}
        output.append(dict(input_hash=key, members=[r['uid'] for r in members],
                           splits=sorted({r['split'] for r in members}),
                           error=visible['error']['error_type'],phase=motion_phase(visible['error']),
                           observed_successful_targets=sorted(targets),
                           candidate_details=[c for c in visible['candidates'] if c['id'] in targets]))
    return output


def failure_phases():
    saved = json.loads((OUTPUT/'hard_failures.json').read_text())
    rows = []
    for row in saved['failures']:
        path = HERE.parent/'hard_cases_v1/tasks'/row['task_id']/'result.json'
        result = json.loads(path.read_text())
        assert not result['success'] and len(result['attempts'])==row['attempts']
        phases = [motion_phase(s['feedback']) for s in result['attempts']]
        assert all(p is not None for p in phases)
        rows.append(dict(task_id=row['task_id'],factor=row['factor'],arm=row['arm'],
                         errors=row['errors'],motion_phases=phases,result_sha256=file_hash(path)))
    return rows


def coverage(records):
    by_id = {r['uid']:r for r in records}
    result = {}
    for split in ('train','dev','legacy_dev'):
        index = lines(OUTPUT/f'{split}_combined.jsonl.index.jsonl')
        count = Counter()
        for row in index:
            labels = {(by_id[uid]['batch'],by_id[uid]['factor']) for uid in row['members']}
            count.update(labels)
        result[split] = [dict(batch=k[0],factor=k[1],n=v) for k,v in sorted(count.items())]
    return result


def main():
    records = lines(OUTPUT/'provenance.jsonl')
    groups = ambiguous(records)
    failures = failure_phases()
    ids = {uid for group in groups for uid in group['members']}
    selected = [r for r in records if r['uid'] in ids]
    report = dict(ambiguous_groups=len(groups),ambiguous_records=len(ids),
                  ambiguous_by_split=dict(Counter(r['split'] for r in selected)),
                  ambiguous_by_error=dict(Counter(g['error'] for g in groups)),
                  ambiguous_by_phase=dict(Counter(g['phase'] for g in groups)),
                  cross_split_ambiguous_groups=sum(len(g['splits'])>1 for g in groups),
                  coverage=coverage(records),failure_count=len(failures),
                  failure_by_family=dict(Counter(r['factor'] for r in failures)),
                  failure_terminal_phase=dict(Counter(r['motion_phases'][-1] for r in failures)),
                  failures_with_error_changes=sum(len(set(r['errors']))>1 for r in failures),
                  explanation='Multiple observed successful targets are not corrupt labels; '
                              'validity for each hidden physical state is not counterfactually established',
                  phase_note='Use motion_phases here; the initial diagnostic phases field queried '
                             'a missing top-level key and is null. Source data and curated messages unchanged.')
    (HERE/'analysis_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    detail = dict(ambiguous_groups=groups,failure_motion_phases=failures,
                  source_manifest_sha256=file_hash(OUTPUT/'manifest.json'),
                  analyzer_sha256=file_hash(Path(__file__)))
    (HERE/'analysis_details.json').write_text(json.dumps(detail,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
