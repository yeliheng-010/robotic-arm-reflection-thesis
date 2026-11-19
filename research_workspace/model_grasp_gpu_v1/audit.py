"""独立进程复算已消费的静态提案，不再次调用模型或执行物理动作。"""
from model_grasp_gpu_v1.common import ROOT, read, save, sha, verify
from model_grasp_gpu_v1.planning import inspect


def main():
    manifest = verify()
    result = read(ROOT/'run/result.json')
    assert result['physical_attempts'] == 0 and result['task_success'] is None
    rows = []
    for folder in sorted((ROOT/'run').glob('plan_*')):
        target = ROOT/'audit'/folder.name
        current = inspect(read(folder/'proposal.json'),manifest,target)
        assert current == read(folder/'result.json')
        for name in ('private_plan.json','private_trace.json','private_events.json','state_check.json'):
            assert read(target/name) == read(folder/name), name
        rows.append(dict(name=folder.name,identical=True,status=current['status']))
    save(ROOT/'audit/result.json',dict(passed=True,plans=rows,physical_attempts=0,
         real_model_calls=0,task_success=None,training_eligible=False,
         run_result_sha256=sha(ROOT/'run/result.json')))
    print(dict(independent_audit=True,plans=len(rows)),flush=True)


if __name__ == '__main__':
    main()
