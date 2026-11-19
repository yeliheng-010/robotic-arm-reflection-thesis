"""复算原始选择与执行动作；不会把模板说明算成模型推理。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import statistics
import random
from stability.collection_status import atomic
from controlled.config import tasks
from bounded.protocol import ROOT,verify
from bounded.candidates import candidates
from bounded.selection import payload,resolve
from bounded.physical import audit
from bounded.baselines import priority
from controlled.worker import jsonlines
from reflection.reflector import Parameters
from flashnext.client import check_response
from nextstudy.prompt import messages
from nextstudy.semantic import action_check,evaluate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic(protocol):
    path = ROOT/'semantic/requests.jsonl'
    events = [json.loads(line) for line in path.read_text().splitlines()]
    fixtures = {f['id']:f for f in protocol['fixtures']}
    assert len({e['id'] for e in events})==len(events)
    assert {e['id'] for e in events}=={f'{f}/{a}/{r}' for f in fixtures
                                     for a in ('guided','hybrid') for r in range(3)}
    for event in events:
        item = fixtures[event['fixture']]
        assert event['text']==check_response(event['response'])
        if event['arm']=='hybrid':
            rows = candidates(item['report'],item['parameters'],item['history'])
            assert rows==event['candidates']
            assert event['request']==payload(item['report'],item['parameters'],rows=rows,history=item['history'])
            # rows 已从同一输入完整重建并与原始候选逐字比较，包含说明文本。
            # 不对JSON落盘后的list再次套用原tuple展示格式，避免仅括号不同的伪失败。
            if event['legal']:
                answer = resolve(event['text'],rows)
                assert answer==event['parsed']
                assert action_check(item,answer['changes'])==event['action_check']
        else:
            assert event['request']['messages']==messages('把指定物体放进指定容器',item['report'],
                       parameters=item['parameters'],history=item['history'],variant='guided')
            recalculated = deepcopy(event)
            evaluate(recalculated,item)
            for field in ('legal','parsed','action_check'):
                assert recalculated.get(field)==event.get(field)
    result = []
    for arm in ('guided','hybrid'):
        rows = [r for r in events if r['arm']==arm]
        result.append(dict(arm=arm,calls=len(rows),legal=sum(r['legal'] for r in rows),
                           compliant=sum(r['action_check']['passed'] for r in rows),
                           service_errors=sum(bool(r.get('service_error')) for r in rows),
                           median_latency_s=statistics.median(r['elapsed_s'] for r in rows) if rows else None))
    return dict(expected=96,completed=len(events),rows=result,requests_verified=True,
                deterministic_explanations_verified=True,source_sha256=sha(path))


def audit_choices(directory,result,item):
    filename = 'selection.jsonl' if item['arm']=='hybrid' else 'baseline_choices.jsonl'
    choices = jsonlines(directory/filename)
    records = [r for r in result['records'] if 'reflection' in r or 'reflection_error' in r]
    assert len(records)==len(choices)
    rng = random.Random(904250+item['case'])
    for record,event in zip(records,choices):
        if item['arm']=='hybrid':
            assert event['text']==check_response(event['response'])
            continue
        parameters = Parameters().updated(record['parameters'])
        rows = event['candidates']
        selected = rng.choice(rows) if item['arm']=='random' else min(rows,key=lambda r:priority(r,parameters))
        assert selected['id']==event['selected'] and event['model'] is None
        assert selected['changes']==record['reflection']['changes']
        assert selected['explanation']==record['reflection']['cause']
    errors = sum('reflection_error' in r for r in records)
    services = sum(bool(e.get('service_error')) for e in choices)
    return dict(calls=len(records),service_errors=services,invalid=errors-services,
                model_latency_s=sum(e.get('elapsed_s',0) for e in choices))


def physical(protocol):
    rows,hashes = [],{}
    for item in protocol['closed_loop']:
        directory = ROOT/'physical/tasks'/item['id']
        if not (directory/'summary.json').exists():
            continue
        result = json.loads((directory/'result.json').read_text())
        audit(directory,result,dict(item,task=tasks()[item['case']]))
        row = json.loads((directory/'summary.json').read_text())
        counts = audit_choices(directory,result,item)
        assert row['success']==result['success'] and row['calls']==counts['calls']
        assert row['service_errors']==counts['service_errors']
        assert row['invalid_outputs']==counts['invalid']+counts['service_errors']
        rows.append(dict(id=item['id'],case=item['case'],arm=item['arm'],repeat=item['repeat'],
                         success=result['success'],attempts=result['attempts'],**counts))
        hashes[item['id']] = sha(directory/'result.json')
    totals = []
    for arm in ('retry','priority','random','hybrid'):
        group = [r for r in rows if r['arm']==arm]
        totals.append(dict(arm=arm,runs=len(group),successes=sum(r['success'] for r in group),
                           invalid=sum(r['invalid'] for r in group),calls=sum(r['calls'] for r in group),
                           service_errors=sum(r['service_errors'] for r in group),
                           model_latency_s=sum(r['model_latency_s'] for r in group)))
    return dict(expected=30,completed=len(rows),rows=rows,metrics=totals,source_hashes=hashes,
                training_approved=0,test_used=False)


def main():
    protocol = verify()
    result = dict(semantic=semantic(protocol),physical=physical(protocol),test_used=False,
                  training_started=False,expansion_started=False)
    atomic(ROOT/'verification.json',result)
    print(json.dumps(dict(semantic=result['semantic'],physical=result['physical']['metrics']),ensure_ascii=False))


if __name__=='__main__':
    main()
