"""新专家worker真实执行及完整结果恢复检查；不并入训练集。"""
import json
from stability.collection_plan import task_plan
from stability.dataset import digest
from stability.experiment import OUT
from stability.expert_audit import audit_task
from stability.expert_worker import execute


def main():
    root = OUT/'expert_worker_smoke_v1'
    for index, task in enumerate(task_plan('pilot')[:2]):
        directory = root/f'{index:05d}'
        result = execute(task, str(directory))
        count = audit_task(directory, task)
        resumed = execute(task, str(directory))
        assert digest(result) == digest(resumed), 'Resume changed completed output'
        print(json.dumps({'case': index, 'samples': count, 'resume_verified': True}), flush=True)


if __name__ == '__main__':
    main()
