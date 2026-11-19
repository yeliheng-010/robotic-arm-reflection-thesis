from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import audit
import sv_audit_replay
import sv_audit_proposal
from sv_common import ROOT, read
from sv_strategy_requests import build
from sv_strategy_actions import check, choose, validate
from sv_strategy_audit import inspect as inspect_attempt, advance

original = audit.inspect


def inspect(case):
    first = read(ROOT/'cases'/case['item']['id']/'first/step.json')
    assert first['strategy'] == case['strategy'] == 'original'
    return original(case)


if __name__ == '__main__':
    with patch.multiple(sv_audit_replay, build=build, check=check, inspect=inspect_attempt, advance=advance), \
         patch.multiple(sv_audit_proposal, validate=validate, choose=choose), patch.object(audit, 'inspect', inspect):
        audit.main()
