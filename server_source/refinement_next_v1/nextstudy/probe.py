"""完整保留 96 个计划调用；无服务重试和响应修复。"""
import json
import os
import random
import time
from controlled.config import MAX_TOKENS
from flashnext.client import generate, append, ready
from flashnext.provenance import identity
from stability.collection_status import atomic
from nextstudy.protocol import ROOT, verify
from nextstudy.prompt import messages
from nextstudy.semantic import evaluate, gate


def run_calls(root, protocol, result):
    order = [(i,v,r) for i in range(len(protocol['fixtures']))
             for v in ('current','guided') for r in range(protocol['repetitions'])]
    random.Random(protocol['order_seed']).shuffle(order)
    atomic(root/'order.json', order)
    for index, variant, repeat in order:
        item = protocol['fixtures'][index]
        prompt = messages('把指定物体放进指定容器', item['report'],
                          parameters=item['parameters'], history=item['history'], variant=variant)
        event = generate(prompt, max_tokens=MAX_TOKENS)
        event.update(id=f"{item['id']}/{variant}/{repeat}", fixture=item['id'],
                     variant=variant, repeat=repeat)
        evaluate(event, item)
        append(root/'requests.jsonl', event)
        result['events'].append(event)
        result['completed'] = len(result['events'])
        atomic(root/'progress.json', {k:result[k] for k in ('status','expected','completed')})
        if event.get('service_error'):
            raise RuntimeError('Service failure; all planned calls retained in denominator')


def main():
    protocol = verify()
    root = ROOT/'semantic'
    root.mkdir(exist_ok=False)
    result = dict(status='running', expected=96, completed=0, events=[],
                  started_at=time.time(), job=os.environ['SLURM_JOB_ID'],
                  models=ready(), identity=identity(), test_used=False, gate_passed=False)
    try:
        run_calls(root, protocol, result)
        verify()
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        result['gate_passed'] = gate([e for e in result['events'] if e['variant']=='guided'])
        atomic(root/'result.json', result)
        atomic(root/'progress.json', {k:result[k] for k in ('status','expected','completed','gate_passed')})


if __name__ == '__main__':
    main()
