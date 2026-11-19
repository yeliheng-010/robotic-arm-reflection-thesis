"""复核原始模型响应并汇总选择、耗时和token，不调用模型。"""
import json
from pathlib import Path
from collections import Counter
from flashnext.client import check_response
from loopstudy.selection import resolve
from loopstudy.protocol import verify
from loopstudy.design import ROOT
from stability.collection_status import atomic


def check_event(decision):
    event=decision['event']
    try:
        text=check_response(event['response'])
        selected=resolve(text,decision['candidates'])
    except (ValueError,KeyError,TypeError):
        assert decision['selected'] is None and decision.get('invalid')
        return False
    assert event['text']==text and decision['selected']==selected
    assert 'invalid' not in decision and 'error' not in event
    return True


def inspect(result):
    rows=[]
    for decision in result['decisions']:
        if 'event' not in decision:
            continue
        valid=check_event(decision)
        event=decision['event']
        rows.append(dict(task=result['item']['id'],after_attempt=decision['after_attempt'],valid=valid,
            phase=decision['feedback']['evidence']['motion_context']['phase'],
            selected=decision['selected'],elapsed_s=event['elapsed_s'],
            usage=event.get('response',{}).get('usage'),service_error=bool(event.get('service_error'))))
    return rows


if __name__=='__main__':
    rows=[]
    for item in verify()['items']:
        path=ROOT/'tasks'/item['id']/'result.json'
        if path.exists():
            rows.extend(inspect(json.loads(path.read_text())))
    output=dict(passed=True,calls=len(rows),valid=sum(r['valid'] for r in rows),
        service_errors=sum(r['service_error'] for r in rows),elapsed_s=sum(r['elapsed_s'] for r in rows),
        prompt_tokens=sum((r['usage'] or {}).get('prompt_tokens',0) for r in rows),
        completion_tokens=sum((r['usage'] or {}).get('completion_tokens',0) for r in rows),
        selected_profiles=dict(Counter(r['selected']['state']['profile'] for r in rows if r['selected'])),rows=rows)
    atomic(ROOT/'model_review.json',output)
    print(json.dumps({k:v for k,v in output.items() if k!='rows'}))
