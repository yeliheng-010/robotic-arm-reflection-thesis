"""每帧先保存观测，再构建提议快照；第四次必须在渲染前拒绝。"""
from f_common import save
from f_requests import build
from live_observations import Sampler, state
from diversity.runtime import digest


def summary(sampler):
    return dict(public=sampler.rows, private=sampler.private,
                additional_observations=max(0, len(sampler.rows)-1), remaining=sampler.budget.remaining)


def observe(lease, case, *, folder, ledger, record, recorder, bridge):
    sampler = Sampler(lease.env, case['config'], item=case['item'], folder=folder/'observations',
                      attempt=1, success=False)
    for index in range(3):
        sampler.capture()
        save(folder/f'observation_summary_{index}.json', summary(sampler))
        bundle = build(ledger, record, sampler=sampler, telemetry=recorder, bridge=bridge)
        save(folder/f'model_input_{index}.json', bundle)
    before = digest(state(lease.env))
    try:
        sampler.capture()
    except ValueError as error:
        assert str(error) == 'Additional observation is unavailable'
    else:
        raise AssertionError('Fourth capture was accepted')
    assert before == digest(state(lease.env))
    assert not (folder/'observations/observation_3').exists()
    save(folder/'observation_budget_check.json', dict(rejected=True, state_unchanged=True,
         count=sampler.budget.count, remaining=sampler.budget.remaining, render_not_started=True))
    save(folder/'observation_summary.json', summary(sampler))
    save(folder/'model_input.json', bundle)
