"""固定闭合控制，先写意图再步进；证据完整度单独计数。"""
import time
from qualified_closure_mjb_v1.protocol import BUDGET, commands
from qualified_closure_dynamics_v1.worker import reasons


def run_loop(backend, sink, *, clock=time.monotonic):
    report = dict(completed_steps=0, observed_steps=-1, uncertain_step=None, reasons=[], error=None)
    started = clock()
    try:
        row = backend.observe()
        sink.observed(0, row)
        report['observed_steps'] = 0
        report['reasons'] = reasons(row)
        for index, command in enumerate(commands(), 1):
            if report['reasons']:
                break
            if clock()-started >= BUDGET['loop_wall_seconds']:
                report['reasons'] = ['wall_timeout']
                break
            sink.intent(index, command)
            report['uncertain_step'] = index
            backend.step(command)
            report['completed_steps'], report['uncertain_step'] = index, None
            row = backend.observe()
            sink.observed(index, row)
            report['observed_steps'] = index
            report['reasons'] = reasons(row)
        if not report['reasons']:
            report['reasons'] = ['budget_exhausted']
    except Exception as error:
        report['reasons'].append('engineering_failure')
        report['error'] = type(error).__name__+': '+str(error)
    return report
