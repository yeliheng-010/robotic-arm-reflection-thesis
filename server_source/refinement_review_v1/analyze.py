"""生成失败索引、重复性计数及按来源隔离的待审候选清单。"""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from screening import catalogue, fingerprint

ROOT = Path('/home/yeliheng/grasp_server/refinement_review_v1')


def request_groups(data):
    groups = defaultdict(list)
    for run in data['runs']:
        for index, event in enumerate(run['events']):
            groups[fingerprint(event['request'])].append(dict(id=f"{run['id']}/a{index+1}",
                parsed='parsed' in event, action=(event.get('parsed') or {}).get('changes'),
                text_sha256=fingerprint(event.get('text')), error=event.get('error')))
    return [dict(sha256=k, calls=len(v), parsed_calls=sum(x['parsed'] for x in v),
                 legal_action_variants=len({fingerprint(x['action']) for x in v if x['parsed']}),
                 text_variants=len({x['text_sha256'] for x in v}), occurrences=v)
            for k, v in groups.items()]


def failures(data):
    result = []
    for run in data['runs']:
        if run['arm'] != 'flash_new' or run['summary']['success']:
            continue
        result.append(dict(id=run['id'], case=run['case'], repeat=run['repeat'],
            task=run['summary']['task'], error_chain=[r['error']['error_type'] for r in run['records']],
            changes=[(r.get('reflection') or {}).get('changes') for r in run['records']],
            invalid_outputs=run['summary']['invalid_outputs'],
            source_files=run['source_files']))
    return sorted(result, key=lambda r: r['id'])


def condition_rows(data):
    rows = []
    for case in sorted({r['case'] for r in data['runs']}):
        row = dict(case=case)
        for arm in ('rule_old', 'rule_new', 'flash_old', 'flash_new'):
            runs = [r for r in data['runs'] if r['case'] == case and r['arm'] == arm]
            row[arm] = dict(runs=len(runs), successes=sum(r['summary']['success'] for r in runs))
        row['model_delta'] = row['flash_new']['successes']-row['flash_old']['successes']
        rows.append(row)
    return rows


def validate(data, candidates):
    assert len(data['runs']) == len(data['audits']) == 96
    assert len({r['id'] for r in data['runs']}) == 96 and all(a['passed'] for a in data['audits'])
    source_files = {}
    for run in [*data['runs'], *data['controls'].values()]:
        source_files.update(run['source_files'])
        assert run['summary']['success'] == any(r['accepted'] for r in run['records'])
        assert run['summary']['calls'] == len(run['feedback'])
    for path, digest in source_files.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    assert all(not c['same_budget_retry_success'] for c in candidates)
    assert all(not c['training_approved'] for c in candidates)
    return dict(passed=True, source_files_verified=len(source_files), runs=96,
                audits=96, test_used=False, raw_training_exported=False)


def summarize_candidates(candidates, transitions):
    summary = {}
    for arm in ('rule_old', 'rule_new', 'flash_old', 'flash_new'):
        rows = [c for c in candidates if c['arm'] == arm]
        summary[arm] = dict(physical_success_transitions=len(rows),
                           unique_state_action_keys=len({r['sample_sha256'] for r in rows}),
                           missing_residual=sum(any(v['measurement']=='missing' for v in r['residual_checks'].values())
                                                for r in rows), training_approved=0)
    return dict(by_arm=summary, candidates=len(candidates), audited_transitions=len(transitions),
                unique_keys_by_source={source: len({r['sample_sha256'] for r in candidates if r['source']==source})
                                       for source in ('llm', 'rule_expert')},
                observed_scene_families=len({fingerprint(r['family']) for r in candidates}),
                label='Candidate counts are not approved training sample counts')


def write_json(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2))


def main():
    data = json.loads((ROOT/'review_data.json').read_text())
    candidates, transitions, groups = catalogue(data)
    verification = validate(data, candidates)
    failed, requests, conditions = failures(data), request_groups(data), condition_rows(data)
    assert len(failed) == 17 and len(conditions) == 12
    analysis = dict(methods=data['final_metrics'], failures=failed, conditions=conditions,
                    candidates=summarize_candidates(candidates, transitions),
                    requests=dict(calls=sum(r['calls'] for r in requests), unique=len(requests),
                                  repeated_groups=sum(r['calls']>1 for r in requests),
                                  varying_action_groups=sum(r['legal_action_variants']>1 for r in requests)),
                    conflicts=[dict(sha256=k, ids=[r['id'] for r in rows]) for k, rows in groups.items()
                               if len({r['next_accepted'] for r in rows}) > 1])
    write_json('analysis.json', analysis)
    write_json('candidates.json', candidates)
    write_json('request_groups.json', requests)
    write_json('verification.json', verification)
    for source in ('llm', 'rule_expert'):
        with (ROOT/(source+'_candidates.jsonl')).open('w') as stream:
            for row in candidates:
                if row['source'] == source:
                    stream.write(json.dumps(row, ensure_ascii=False)+'\n')
    print(json.dumps({k: analysis[k] for k in ('candidates', 'requests', 'conflicts')}))


if __name__ == '__main__':
    main()
