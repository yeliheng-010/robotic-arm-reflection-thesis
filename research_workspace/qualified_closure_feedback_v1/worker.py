import subprocess
import traceback
from reflection.__main__ import bootstrap
bootstrap()
from qualified_closure_feedback_v1.common import ROOT, RUN, SEED, MAX_DECISIONS, read, save, verify
from qualified_closure_feedback_v1 import inputs, policy, budget
from qualified_closure_feedback_v1.preflight import evaluate


def decision(ordinal, *, context, history):
    folder = RUN / f'decision_{ordinal}'
    request = policy.request(context, history, remaining=MAX_DECISIONS - ordinal + 1)
    save(folder / 'request.json', request)
    budget.reserve(ordinal)
    try:
        subprocess.run(['bash', str(ROOT / 'model.sh'), str(ordinal)], check=True, timeout=360)
        parsed = read(folder / 'validated.json')
        if not parsed['valid']:
            result = dict(status='invalid_model_output', stage=None)
        else:
            result = evaluate(parsed['action'], history=history, geometry=context['geometry'], folder=folder)
    except Exception:
        save(folder / 'engineering_failure.json', dict(traceback=traceback.format_exc()))
        result = dict(status='engineering_failure', stage=None)
    save(folder / 'result.json', result)
    print(dict(ordinal=ordinal, **result), flush=True)
    return result


def main():
    verify()
    save(RUN / 'run_started.json', dict(max_decisions=MAX_DECISIONS))
    context, history, rows = inputs.context(SEED), inputs.history(), []
    for ordinal in range(1, MAX_DECISIONS + 1):
        result = decision(ordinal, context=context, history=history)
        rows.append(dict(ordinal=ordinal, **result))
        if result['status'] != 'rejected':
            break
        parsed = read(RUN / f'decision_{ordinal}/validated.json')
        history.append(policy.entry(parsed['action'], result['stage']))
    verify()
    save(RUN / 'result.json', dict(rows=rows, model_reservations=len(rows),
         generations_started=len(list(RUN.glob('decision_*/generation_started.json'))),
         responses_saved=len(list(RUN.glob('decision_*/response.json'))),
         ready_ordinal=next((r['ordinal'] for r in rows if r['status'] == 'ready'), None),
         physical_attempts=0, training_runs=0))


if __name__ == '__main__':
    main()
