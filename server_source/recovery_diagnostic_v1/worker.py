"""单任务独立进程，原资格审计和物理执行完整复用。"""
import argparse
import importlib
import time
from unittest.mock import patch
from common import ROOT,read,save,verify,sha
from client import generate
from audit_task import audit
from variant import configured
from loopstudy import selection


def execute(entry):
    qualified=importlib.import_module(entry['package']+'.tasks').qualification(entry['item'])
    assert qualified['eligible']==entry['eligible'] and qualified['status']==entry['qualification_status']
    directory=ROOT/'tasks'/entry['uid']
    started=time.monotonic()
    if not qualified['eligible']:
        directory.mkdir(parents=True,exist_ok=False)
        row=dict(uid=entry['uid'],method=entry['method'],executed=False,status='skipped_ineligible',
                 success=None,attempts=0,calls=0,invalid=0,service_errors=0)
    else:
        episode=importlib.import_module(entry['package']+'.episode')
        def call(messages,*,max_tokens):
            return generate(entry['method'],messages,max_tokens=max_tokens)
        with configured(entry),patch.object(selection,'generate',call):
            result=episode.run(entry['item'],directory)
        checked=audit(result,entry)
        row=dict(uid=entry['uid'],method=entry['method'],executed=True,status=result['status'],
                 success=result['success'],audit=checked,**{k:v for k,v in checked.items() if k!='passed'},
                 result_sha256=sha(directory/'result.json'),first_success=result['attempts'][0]['success'],
                 call_elapsed_s=sum(d.get('event',{}).get('elapsed_s',0) for d in result['decisions']))
    row.update(elapsed_s=time.monotonic()-started,training_approved=0,test_used=False,
               variant=entry['variant'],max_attempts=entry['max_attempts'])
    save(directory/'summary.json',row)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('index',type=int)
    index=parser.parse_args().index
    execute(verify()['entries'][index])
