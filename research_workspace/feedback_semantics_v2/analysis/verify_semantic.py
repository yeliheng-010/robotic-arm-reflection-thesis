"""从冻结协议与原始请求复算事实读取结果，不发起模型调用。"""
import json
from pathlib import Path
import random
import sys

ROOT = Path('/home/yeliheng/grasp_server/feedback_semantics_v2')
sys.path.insert(0,str(ROOT))
from probe_semantics import fixtures,request_messages,evaluate,ORDER_SEED,REPEATS,MAX_TOKENS
from semanticfix2.protocol import verify,sha
from flashnext.client import check_response,MODEL
from stability.collection_status import atomic

METRICS = ('valid','phase_correct','bodies_supported','detail_complete')


def verify_event(event,fixture,order):
    index,arm,repeat = order
    assert event['id']==f"{fixture['id']}/{arm}/{repeat}"
    assert (event['fixture'],event['arm'],event['repeat'])==(index,arm,repeat)
    expected = dict(model=MODEL,messages=request_messages(fixture,arm),temperature=0,seed=42,
                    max_tokens=MAX_TOKENS,chat_template_kwargs={'enable_thinking':False})
    assert event['request']==expected
    try:
        response_text = check_response(event['response'])
    except (ValueError,KeyError,TypeError):
        assert 'error' in event and 'text' not in event
    else:
        assert event['text']==response_text and 'error' not in event
    assert event['score']==evaluate(event,fixture,arm)


def aggregate(rows,values):
    totals = []
    for group in ('all','physical','synthetic'):
        for arm in ('legacy','explicit'):
            selected = [r for r in rows if r['arm']==arm and (group=='all' or
                        values[r['fixture']]['synthetic']==(group=='synthetic'))]
            totals.append(dict(group=group,arm=arm,n=len(selected),
                               **{k:sum(r['score'][k] for r in selected) for k in METRICS}))
    return totals


def main():
    verify()
    directory = ROOT/'semantic'
    protocol = json.loads((directory/'protocol.json').read_text())
    assert protocol['code_sha256']==sha(ROOT/'analysis/probe_semantics.py')
    assert protocol['physical_protocol_sha256']==sha(ROOT/'protocol.json')
    assert protocol['max_tokens']==MAX_TOKENS
    values = fixtures()
    assert values==protocol['fixtures'] and len(values)==6
    order = [[i,a,r] for i in range(len(values)) for a in ('legacy','explicit') for r in range(REPEATS)]
    random.Random(ORDER_SEED).shuffle(order)
    assert order==protocol['order']
    result = json.loads((directory/'result.json').read_text())
    rows = [json.loads(line) for line in (directory/'requests.jsonl').read_text().splitlines()]
    assert result['rows']==rows and result['completed']==len(rows)
    assert result['status']=='completed' and result['expected']==len(rows)==len(order)==24
    assert len({r['id'] for r in rows})==24
    for event,entry in zip(rows,order):
        verify_event(event,values[entry[0]],entry)
    summary = dict(passed=True,expected=24,completed=24,metrics=aggregate(rows,values),
                   task='feedback_fact_reading',model=MODEL,training_approved=0,
                   protocol_sha256=sha(directory/'protocol.json'),requests_sha256=sha(directory/'requests.jsonl'))
    atomic(ROOT/'semantic_verification.json',summary)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
