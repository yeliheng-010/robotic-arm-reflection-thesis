"""单任务进程隔离策略补丁，保留每一步原始物理结果。"""
import argparse
import importlib
import time
from common import ROOT,save,verify,sha
from policy import configured
from audit_task import audit


def execute(entry):
    qualified=importlib.import_module(entry['package']+'.tasks').qualification(entry['item'])
    assert qualified['eligible']==entry['eligible'] and qualified['status']==entry['qualification_status']
    directory=ROOT/'tasks'/entry['uid']
    started=time.monotonic()
    if not qualified['eligible']:
        directory.mkdir(parents=True,exist_ok=False)
        row=dict(executed=False,status='skipped_ineligible',success=None,attempts=0,calls=0,invalid=0,service_errors=0)
    else:
        episode=importlib.import_module(entry['package']+'.episode')
        with configured(entry):
            result=episode.run(entry['item'],directory)
        checked=audit(result,entry)
        row=dict(executed=True,status=result['status'],success=result['success'],audit=checked,
                 **{k:v for k,v in checked.items() if k!='passed'},
                 result_sha256=sha(directory/'result.json'),first_success=result['attempts'][0]['success'],
                 call_elapsed_s=sum(d.get('event',{}).get('elapsed_s',0) for d in result['decisions']))
    row.update(uid=entry['uid'],method=entry['method'],max_attempts=entry['max_attempts'],
               elapsed_s=time.monotonic()-started,training_approved=0,test_used=False)
    save(directory/'summary.json',row)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('index',type=int)
    execute(verify()['entries'][parser.parse_args().index])
