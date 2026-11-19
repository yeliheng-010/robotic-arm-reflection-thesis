"""相同合成输入比较原guided与新混合方法，保留全部分母。"""
import os
import random
import time
from controlled.config import MAX_TOKENS
from flashnext.client import generate as free_generate, append, ready
from stability.collection_status import atomic
from nextstudy.prompt import messages
from nextstudy.semantic import evaluate, action_check
from bounded.protocol import ROOT,verify
from bounded.candidates import candidates
from bounded.selection import generate


def run_one(item, arm):
    if arm=='guided':
        prompt = messages('把指定物体放进指定容器',item['report'],parameters=item['parameters'],
                          history=item['history'],variant='guided')
        event = free_generate(prompt,max_tokens=MAX_TOKENS)
        evaluate(event,item)
        return event
    rows = candidates(item['report'],item['parameters'],item['history'])
    event = generate(item['report'],item['parameters'],rows=rows,history=item['history'])
    event.update(candidates=rows,legal='parsed' in event,action_check={'passed':False})
    if event['legal']:
        event['action_check'] = action_check(item,event['parsed']['changes'])
    return event


def main():
    protocol = verify()
    root = ROOT/'semantic'
    root.mkdir(exist_ok=False)
    order = [(i,a,r) for i in range(16) for a in ('guided','hybrid') for r in range(3)]
    random.Random(protocol['semantic_seed']).shuffle(order)
    atomic(root/'order.json',order)
    result = dict(status='running',expected=96,completed=0,events=[],job=os.environ['SLURM_JOB_ID'],
                  models=ready(),started_at=time.time(),gate_passed=False,test_used=False)
    try:
        for index,arm,repeat in order:
            item = protocol['fixtures'][index]
            event = run_one(item,arm)
            event.update(id=f"{item['id']}/{arm}/{repeat}",fixture=item['id'],arm=arm,repeat=repeat)
            append(root/'requests.jsonl',event)
            result['events'].append(event)
            result['completed'] += 1
            atomic(root/'progress.json',{k:result[k] for k in ('status','expected','completed')})
            if event.get('service_error'):
                raise RuntimeError('Service error; retain denominator and stop')
        selected = [e for e in result['events'] if e['arm']=='hybrid']
        result['gate_passed'] = len(selected)==48 and all(e['legal'] and e['action_check']['passed'] for e in selected)
        verify()
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed',error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(root/'result.json',result)
        atomic(root/'progress.json',{k:result[k] for k in ('status','expected','completed','gate_passed')})


if __name__=='__main__':
    main()
