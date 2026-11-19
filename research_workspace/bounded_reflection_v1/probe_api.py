"""测试服务是否真正约束输出，原始请求及不合规响应全部保存。"""
import json
import os
from pathlib import Path
import time
from flashnext.client import request, check_response, append, MODEL
from stability.collection_status import atomic

ROOT = Path('/home/yeliheng/grasp_server/bounded_reflection_v1')


def probes():
    return [dict(kind=kind, value=value, definition=definition)
            for kind,definition,values in (
                ('number',{'type':'number','minimum':-.25,'maximum':.25},(.31,-.31)),
                ('integer',{'type':'integer','minimum':-250,'maximum':250},(310,-310)),
                ('enum',{'type':'string','enum':['choice_a_946','choice_b_731']},('outside','unknown')))
            for value in values]


def compliant(item, value):
    if item['kind']=='enum':
        return value in item['definition']['enum']
    kind = type(value) is int if item['kind']=='integer' else type(value) in (int,float)
    return kind and item['definition']['minimum'] <= value <= item['definition']['maximum']


def main():
    assert os.environ.get('SLURM_JOB_ID')
    root = ROOT/'capability'
    root.mkdir(exist_ok=False)
    rows = []
    for index,item in enumerate(probes()):
        schema = dict(type='object',properties={'value':item['definition']},
                      required=['value'],additionalProperties=False)
        payload = dict(model=MODEL,temperature=0,seed=42,max_tokens=128,
                       chat_template_kwargs={'enable_thinking':False},
                       messages=[{'role':'user','content':'Return exactly this JSON value without modification: '+
                                  json.dumps({'value':item['value']})}],
                       response_format={'type':'json_schema','json_schema':{
                           'name':'bounded_probe','strict':True,'schema':schema}})
        event = dict(id=index,item=item,request=payload,started_at=time.time(),passed=False)
        try:
            event['response'] = request('/chat/completions',payload)
            event['text'] = check_response(event['response'])
            value = json.loads(event['text'])
            event['passed'] = set(value)=={'value'} and compliant(item,value['value'])
        except Exception as error:
            event['error'] = repr(error)
        append(root/'requests.jsonl',event)
        rows.append(event)
    atomic(root/'result.json',dict(completed=6,job=os.environ['SLURM_JOB_ID'],rows=rows))
    print(json.dumps([dict(kind=r['item']['kind'],passed=r['passed'],text=r.get('text'),error=r.get('error'))
                      for r in rows],ensure_ascii=False))


if __name__=='__main__':
    main()
