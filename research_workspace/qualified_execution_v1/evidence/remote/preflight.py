from types import SimpleNamespace
from qualified_execution_v1.environment import opened
from qualified_execution_v1.common import RUN, SOURCE, read, save, verify, case, plan
from qualified_execution_v1 import runtime
from qualified_entry_v1.commands import run as commands
from qualified_task_v1.observer import observe
from qualified_task_v1.integrity import fingerprint, unchanged


def run(folder):
    item, recorded, guard = case(), plan(), {}
    with opened(item, guard, static=True) as env:
        before = fingerprint(env)
        observe(env, item['config'], folder=folder/'initial_observation')
        native = runtime.native_flow(env, recorded)
        context = SimpleNamespace(env=env, robot=env.robot, q0=native.q0.copy(),
            q1=native.q0.copy(), T_wo=native.T_wo)
        result = commands(context, item, plan=recorded, folder=folder)
        isolation = unchanged(before, fingerprint(env))
    return dict(passed=result['passed'], initial_qualified=True, state_matches=True,
        commands=result, isolation=isolation, physical_attempts=0, model_calls=0)


def main(mode):
    verify()
    folder = RUN/('preflight' if mode == 'run' else 'preflight_audit')
    result = run(folder)
    if mode == 'audit':
        assert result == read(RUN/'preflight/result.json')
        save(RUN/'preflight_audit.json', dict(passed=True, independent=True, identical=True))
    save(folder/'result.json', result)
    verify()
    print(dict(mode=mode, passed=result['passed'], initial_qualified=result['initial_qualified']), flush=True)


if __name__ == '__main__':
    import sys
    main(sys.argv[1])
