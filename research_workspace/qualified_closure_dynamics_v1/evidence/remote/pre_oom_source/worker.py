"""无仿真依赖的固定预算循环；后端仅允许一次原生步进。"""
import time
from qualified_closure_dynamics_v1.protocol import BUDGET, commands


def reasons(row):
    result = []
    if row['cached_hits']:
        result.append('cached_collision')
    if row['rebuilt_hits']:
        result.append('rebuilt_collision')
    result.extend(key for key in ('nonfinite', 'warnings', 'model_changed') if row[key])
    result.extend(row.get('initial_rejections', []))
    return result


def run_loop(backend, sink, *, clock=time.monotonic):
    report = dict(completed_steps=0, uncertain_step=None, reasons=[], error=None)
    started = clock()
    try:
        row = backend.observe()
        sink.observed(0, row)
        report['reasons'] = reasons(row)
        for index, command in enumerate(commands(), 1):
            if report['reasons']:
                break
            if clock() - started >= BUDGET['loop_wall_seconds']:
                report['reasons'] = ['wall_timeout']
                break
            sink.intent(index, command)
            report['uncertain_step'] = index
            backend.step(command)
            report['completed_steps'] = index
            report['uncertain_step'] = None
            row = backend.observe()
            sink.observed(index, row)
            report['reasons'] = reasons(row)
        if not report['reasons']:
            report['reasons'] = ['budget_exhausted']
    except Exception as error:
        report['reasons'].append('engineering_failure')
        report['error'] = type(error).__name__ + ': ' + str(error)
    return report
