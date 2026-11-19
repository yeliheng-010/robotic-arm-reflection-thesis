"""仅扩展已证实端点可行而前缀阻塞的固定条件。"""
import sys
from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
from cp_probe import inspect
from cp_common import current as source_case
from pg_scope import context
from qs_probe import endpoints
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'probe'
NAME = 'F0_964345_varied_noisy'


def main(mode):
    assert mode in ('probe','audit')
    verify(RUN/'manifest.json')
    row = source_case(NAME)
    source = ROOT.parent/'qualification_strategy_v1/actual/cases'/NAME/'result.json'
    case = verify(source)['case']
    ledger = []
    with context(case['item'], ledger):
        plan, trace = inspect(row)
    if mode == 'audit':
        assert plan == read(RUN/'probe/plan.json')
        assert ledger == read(RUN/'probe/ledger.json')
    output = RUN/mode
    save(output/'plan.json', plan)
    save(output/'ledger.json', ledger)
    save(output/'result.json', dict(passed=True, qualified=plan['selected'] is not None,
        independent=mode == 'audit', trace=trace, endpoints=endpoints(plan), status=plan['status'],
        selected=(plan['selected'] or {}).get('id'), checked_joint_routes=sum(len(r['attempts']) for r in ledger),
        unique_prefix_endpoints=len(ledger), physical_attempts=0, model_calls=0,
        identities={str(p):sha(p) for p in (output/'plan.json',output/'ledger.json')}))
    print(dict(mode=mode, qualified=plan['selected'] is not None, status=plan['status'],
        prefix=len(plan['prefixes']), carry=len(plan['candidates']), endpoints=len(ledger)), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
