"""仅恢复首次成功导致的缺失汇总；完整物理结果和失败日志保持不变。"""
import json
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.loop_freeze import ROOT, verify
from stability.loop_audit import audit
from stability.loop_protocol import ARMS, summarize
from stability.loop_results import reconstruct
from stability.sft_freeze import file_hash


def recover_summary(directory, row):
    target = directory/'summary.json'
    if target.exists():
        assert json.loads(target.read_text()) == row
        return False
    assert row['arm'] in ('base', 'adapted') and row['success'] is True
    assert row['attempts'] == 1 and row['calls'] == 0 and row['invalid'] == 0
    assert not (directory/'requests.jsonl').exists()
    log = (ROOT/f"task_{row['case']:02d}_{row['arm']}.log").read_text()
    assert 'FileNotFoundError' in log and 'requests.jsonl' in log
    with target.open('x') as stream:
        json.dump(row, stream, ensure_ascii=False, indent=2)
    return True


def main():
    config = verify()
    assert (ROOT/'failure.json').exists() and not (ROOT/'result.json').exists()
    failure = json.loads((ROOT/'failure.json').read_text())
    assert 'CalledProcessError' in failure['error']
    paths = sorted((ROOT/'tasks').glob('*/*/result.json'))
    assert len(paths) == len(config['tasks'])*len(ARMS) == 24
    before = {str(p.relative_to(ROOT)): file_hash(p) for p in paths}
    rows, repaired = [], []
    for case in range(len(config['tasks'])):
        for arm in ARMS:
            directory = ROOT/'tasks'/f'{case:02d}'/arm
            row = reconstruct(directory, case=case, arm=arm)
            if recover_summary(directory, row):
                repaired.append({'case': case, 'arm': arm})
            rows.append(row)
    verification = audit(config, rows)
    assert before == {str(p.relative_to(ROOT)): file_hash(p) for p in paths}
    record = dict(reason='first_attempt_success_requires_no_model_request_log', repaired=repaired,
        raw_files_unchanged=before, failed_job='3717', failure_sha256=file_hash(ROOT/'failure.json'),
        recovery_code={n: file_hash(OUT/'stability'/n) for n in ('loop_results.py', 'loop_finalize.py')})
    atomic(ROOT/'completion_recovery.json', record)
    atomic(ROOT/'result.json', dict(status='completed', metrics=summarize(rows), verification=verification,
        rows=rows, test_used=False, finalization='audited_metadata_recovery_after_job_error'))
    print(json.dumps({'verification': verification, 'metrics': summarize(rows), 'repaired': repaired}))


if __name__ == '__main__':
    main()
