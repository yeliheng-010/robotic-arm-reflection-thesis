"""穷举既有Top-5诊断接近可执行性；不导出教师样本。"""
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
from stability.experiment import OUT


def execute(index):
    from reflection.__main__ import bootstrap
    bootstrap()
    from stability.runtime import StableEngine

    class ProbeEngine(StableEngine):
        def _attempt(self, *args, **kwargs):
            values = list(args)
            values[5] = values[5].updated({'candidate_index': index})
            return super()._attempt(*values, **kwargs)

    engine = ProbeEngine(max_attempts=1, headless=True, task_parser='rule', scene_jitter=.012)
    try:
        result = engine.run(source='OrangeSphere', destination='BlueBin', fault='collision',
            seed=2000, method='baseline', output=OUT/'candidate_probe'/str(index))
        record = result['records'][0]
        error = record['error'] or {}
        return dict(index=index, success=result['success'], error=error.get('error_type'),
            segment=record['diagnostics'].get('motion_segment'), evidence=error.get('evidence'))
    finally:
        engine.close()


def main():
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn')) as pool:
        rows = list(pool.map(execute, range(5)))
    (OUT/'candidate-probe.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps([{k: v for k, v in r.items() if k != 'evidence'} for r in rows]))


if __name__ == '__main__':
    main()

