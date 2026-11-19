"""单卡完成全部冻结输入诊断；模型释放后再分配四卡物理对照。"""
import time
import traceback
from od_common import ROOT,verify,save,MAX_CALLS
from od_generator import Generator,replay
from od_api import payload
from od_records import tasks,prepare,decode,audit_record


def main():
    manifest=verify()
    directory=ROOT/'model_records'
    directory.mkdir(exist_ok=False)
    status=dict(status='loading',completed=0,expected=MAX_CALLS,started_at=time.time())
    save(ROOT/'model_progress.json',status)
    try:
        generator=Generator()
        startup=replay(generator)
        save(ROOT/'model_startup.json',dict(passed=True,replay=startup,environment=generator.environment))
        status['status']='running'
        for task in tasks(manifest):
            request=payload(prepare(task))
            response=generator.generate(request)
            record=dict(task=task,request=request,response=response,
                result=decode(task,request['messages'],response))
            save(directory/f"{task['id']}.json",record)
            audit_record(record,task)
            status['completed']+=1
            status['last_task']=task['id']
            save(ROOT/'model_progress.json',status)
        status['status']='completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        status['ended_at']=time.time()
        save(ROOT/'model_progress.json',status)


if __name__=='__main__':
    main()
