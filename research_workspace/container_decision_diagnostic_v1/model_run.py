"""全部模型请求先于新物理标签生成。"""
import time
from cd_common import ROOT, verify, save
from cd_design import request
from cd_generator import Generator, replay
from cd_records import tasks, decode, audit_record


def main():
    manifest = verify()
    folder = ROOT/'model_records'
    folder.mkdir(exist_ok=False)
    status = dict(status='loading',completed=0,expected=44,started_at=time.time())
    save(ROOT/'model_progress.json',status)
    try:
        generator = Generator()
        startup = replay(generator)
        save(ROOT/'model_startup.json',dict(passed=True,replay=startup,environment=generator.environment))
        status['status'] = 'running'
        for task in tasks(manifest):
            case = manifest['cases'][task['case_index']]
            body = request(case,task['variant'])
            response = generator.generate(body)
            record = dict(task=task,request=body,response=response,result=decode(response,case))
            save(folder/f"{task['id']}.json",record)
            audit_record(record,task,manifest)
            status.update(completed=status['completed']+1,last_task=task['id'])
            save(ROOT/'model_progress.json',status)
        status['status'] = 'completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        status['ended_at'] = time.time()
        save(ROOT/'model_progress.json',status)


if __name__ == '__main__':
    main()
