"""核对并行调度没有改变同任务的参数、物理结果和监督输入。"""
import argparse
import json
import numpy as np
from stability.dataset import digest
from stability.experiment import OUT


def compare(root, total):
    baseline = OUT/'expert_batch_v1'
    for index in range(total):
        name = f'{index:05d}'
        left = json.loads((baseline/'tasks'/name/'summary.json').read_text())
        right = json.loads((root/'tasks'/name/'summary.json').read_text())
        assert left['task'] == right['task']
        assert digest([r['messages'] for r in left['samples']]) == digest([r['messages'] for r in right['samples']])
        for arm in ('expert_result', 'retry_result'):
            a = json.loads(__import__('pathlib').Path(left[arm]).read_text())
            b = json.loads(__import__('pathlib').Path(right[arm]).read_text())
            assert a['success'] == b['success'] and len(a['records']) == len(b['records'])
            for x, y in zip(a['records'], b['records']):
                for field in ('parameters', 'accepted', 'physical_success'):
                    assert x[field] == y[field]
                np.testing.assert_allclose(x['evaluation']['position'], y['evaluation']['position'], atol=1e-8, rtol=0)
    print(json.dumps({'paired_tasks': total, 'physical_and_messages_equal': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--count', type=int, required=True)
    args = parser.parse_args()
    compare(OUT/args.run, args.count)
