"""独立核验每个计划条目及重复初态，产出不删失败的阶段摘要。"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
from stability.collection_status import atomic
from nextstudy.protocol import ROOT, verify
from nextstudy.physical import audit
from nextstudy.design import item_scenario
from nextstudy.prompt import messages
from nextstudy.semantic import evaluate, gate
from controlled.config import MAX_TOKENS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical(protocol):
    groups, rows, hashes = defaultdict(list), [], {}
    for item in protocol['physical']:
        path = ROOT/'physical/tasks'/item['id']/'result.json'
        if not (path.parent/'summary.json').exists():
            continue
        result = json.loads(path.read_text())
        assert result['item'] == item and result['scenario'] == item_scenario(item)
        audit(result,item)
        hashes[str(path)] = digest(path)
        record = result['records'][0]
        row = dict(id=item['id'],case=item['case'],factors=item['factors'],
                   success=result['success'],error=(record.get('error') or {}).get('error_type'),
                   segment=record['diagnostics'].get('motion_segment'),
                   initial=record['candidate_trace'],evaluation=record['evaluation'])
        rows.append(row)
        key = json.dumps([item['case'],item['factors']],sort_keys=True)
        groups[key].append(row)
    pairs = []
    for key, entries in groups.items():
        first = entries[0]
        for other in entries[1:]:
            for field in ('initial_qpos','initial_body_xyz'):
                np.testing.assert_allclose(first['initial'][field],other['initial'][field],atol=1e-8,rtol=0)
        pairs.append(dict(case=first['case'],factors=first['factors'],runs=len(entries),
                          successes=sum(r['success'] for r in entries),
                          outcomes=[(r['error'],r['segment']) for r in entries]))
    invariance = feedback_invariance(rows)
    return dict(expected=40,completed=len(rows),all_audited=True,cells=pairs,source_hashes=hashes,
                feedback_invariance_pairs=invariance,
                training_approved=0,model_calls=0)


def feedback_invariance(rows):
    groups = defaultdict(list)
    for row in rows:
        if row['case'] == 47:
            factors = row['factors']
            key = (factors['layout'],factors['physics'],row['id'].split('_r')[-1])
            groups[key].append(row)
    checked = 0
    for group in groups.values():
        if len(group) != 2:
            continue
        first,other = group
        assert first['success']==other['success'] and first['error']==other['error']
        for field in ('initial_qpos','initial_body_xyz'):
            np.testing.assert_allclose(first['initial'][field],other['initial'][field],atol=1e-8,rtol=0)
        np.testing.assert_allclose(first['evaluation']['position'],other['evaluation']['position'],atol=1e-8,rtol=0)
        checked += 1
    return checked


def semantic(protocol):
    path = ROOT/'semantic/requests.jsonl'
    events = [json.loads(line) for line in path.read_text().splitlines()]
    fixtures = {r['id']:r for r in protocol['fixtures']}
    expected = {(f,v,r) for f in fixtures for v in ('current','guided') for r in range(3)}
    observed = {(e['fixture'],e['variant'],e['repeat']) for e in events}
    assert len(observed) == len(events) and observed <= expected
    annotations = ROOT/'semantic_annotations.json'
    reviews = json.loads(annotations.read_text())['events'] if annotations.exists() else {}
    for event in events:
        item = fixtures[event['fixture']]
        request = event['request']
        assert request['messages'] == messages('把指定物体放进指定容器',item['report'],
                    parameters=item['parameters'],history=item['history'],variant=event['variant'])
        assert request['max_tokens']==MAX_TOKENS and request['temperature']==0 and request['seed']==42
        rerun = json.loads(json.dumps(event))
        evaluate(rerun,item)
        assert rerun['legal']==event['legal'] and rerun['action_check']==event['action_check']
        event['rationale_review'] = reviews.get(event['id'],{}).get('status','pending')
    rows = []
    for variant in ('current','guided'):
        selected = [e for e in events if e['variant']==variant]
        rows.append(dict(variant=variant,calls=len(selected),legal=sum(e['legal'] for e in selected),
                         strategy_compliant=sum(e['action_check']['passed'] for e in selected),
                         service_errors=sum(bool(e.get('service_error')) for e in selected),
                         reviewed=sum(e['rationale_review']!='pending' for e in selected),gate_passed=gate(selected)))
    return dict(expected=96,completed=len(events),rows=rows,raw_sha256=digest(path),
                full_request_verified=True,automatic_action_check_reproduced=True,
                gate_passed=next(r['gate_passed'] for r in rows if r['variant']=='guided'))


def main():
    protocol = verify()
    result = dict(physical=physical(protocol),semantic=semantic(protocol),test_used=False,
                  development_regression_started=False,expansion_started=False,new_training_started=False)
    atomic(ROOT/'analysis.json',result)
    concise = {k:{x:v[x] for x in ('completed','expected')} for k,v in result.items() if isinstance(v,dict)}
    print(json.dumps(dict(progress=concise,semantic=result['semantic']['rows']),ensure_ascii=False))


if __name__ == '__main__':
    main()
