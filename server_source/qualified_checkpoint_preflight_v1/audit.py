"""独立静态复算；仅比较实际经过的分支，不新增模型动作。"""
import os
from qualified_checkpoint_preflight_v1.worker import run
from qualified_checkpoint_preflight_v1.protocol import ROOT, RUN, read, save, sha, verify


def main():
    manifest = verify()
    frozen = {str(p): sha(p) for p in RUN.rglob('*') if p.is_file()}
    save(RUN / 'audit_claim.json', dict(consumed=1, input_sha256=manifest['input_sha256']))
    assert read(RUN / 'preflight_claim.json') == dict(consumed=1, input_sha256=manifest['input_sha256'])
    result = run(RUN / 'audit')
    assert result == read(RUN / 'preflight/result.json')
    compared = []
    for name in ('proposal.json', 'private_plan.json', 'closure.json', 'commands.json',
                 'preflight.json', 'zero_motion_guard.json'):
        left, right = RUN / 'preflight' / name, RUN / 'audit' / name
        assert left.exists() == right.exists(), name
        if left.exists():
            assert read(left) == read(right), name
            compared.append(name)
    for name, expected in frozen.items():
        assert sha(name) == expected, name
    verify()
    save(RUN / 'audit_result.json', dict(passed=True, independent_process=True, result=result,
         compared=compared, frozen_primary_outputs=frozen, job=os.environ['SLURM_JOB_ID'],
         model_calls=0, physical_attempts=0, training_runs=0, audit_source_sha256=sha(ROOT / 'audit.py')))
    print(dict(passed=True, result=result, compared=compared), flush=True)


if __name__ == '__main__':
    main()
