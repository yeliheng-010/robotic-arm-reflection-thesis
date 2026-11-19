"""独立进程加密采样与评价回放，不调用物理执行入口。"""
import numpy as np
from qualified_execution_v1.environment import opened
from qualified_execution_v1.common import case
from qualified_task_v1.integrity import fingerprint, unchanged
from qualified_closure_v1.common import RUN, read, save, verify
from qualified_closure_v1.geometry import sweep, SAMPLE_COUNT
from qualified_closure_v1.evaluation import replay
from qualified_closure_v1.worker import commanded_endpoint


def main():
    verify()
    prior = read(RUN / 'closure.json')
    item = case()
    with opened(item, {}, static=True) as env:
        before = fingerprint(env)
        command, _ = commanded_endpoint(env, item)
        np.testing.assert_array_equal(command, prior['command'])
        dense = sweep(env, item['item'], command=command, sample_count=2 * SAMPLE_COUNT - 1)
        assert dense['rows'][::2] == prior['rows']
        assert not dense['passed'] and not prior['passed']
        assert all(row['valid'] for row in dense['rows'])
        assert any(row['contacts'] for row in dense['rows'])
        evaluations = {name: replay(env.mj_model, RUN / name)
                       for name in ('restored_terminal', 'synthetic_stale_cache')}
        isolation = unchanged(before, fingerprint(env))
    verify()
    result = dict(passed=True, independent_process=True, original_samples_exact=True,
                  dense_samples=dense['samples'], dense_collision_samples=sum(bool(r['contacts']) for r in dense['rows']),
                  evaluations=evaluations, isolation=isolation,
                  physical_attempts=0, model_calls=0, training_runs=0)
    save(RUN / 'dense_closure.json', dense)
    save(RUN / 'audit.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
