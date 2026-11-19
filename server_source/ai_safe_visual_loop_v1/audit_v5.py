"""保留 v4 冻结执行，只修正独立审计的观测引用位置。"""
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import audit
import audit_v4
import top_audit
import sv_strategy_audit
import sv_audit_replay
import sv_audit_proposal
from observation_reference_v5 import observation


def audit_attempt(case, step):
    original = top_audit.read
    target = Path(step['session_path'])/'observation_summary.json'

    def read(path):
        return observation(step) if Path(path) == target else original(path)

    with patch.object(top_audit, 'read', read):
        return top_audit.audit_attempt(case, step)


if __name__ == '__main__':
    with patch.multiple(sv_audit_replay, build=audit_v4.build, check=audit_v4.check,
                        inspect=audit_v4.inspect_attempt, advance=audit_v4.advance), \
         patch.multiple(sv_audit_proposal, validate=audit_v4.validate, choose=audit_v4.choose), \
         patch.object(sv_strategy_audit, 'audit_attempt', audit_attempt), \
         patch.object(audit, 'inspect', audit_v4.inspect):
        audit.main()
