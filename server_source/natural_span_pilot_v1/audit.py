from pathlib import Path
from unittest.mock import patch
import qp_audit
from span_audit import context
from sp_common import ROOT, read, verify, change, ACTIONS

original_route, original_inspect = qp_audit.route, qp_audit.inspect


def route(case, step, record):
    folder = Path(step['session_path'])
    calibration = read(folder/'observation_summary.json')['private'][0]
    with context(folder, calibration):
        return original_route(case, step, record)


def inspect(case):
    row = original_inspect(case)
    assert all(step['contacts']['self_contact_samples'] == 0 for step in row['rows'])
    return row


if __name__ == '__main__':
    with patch.multiple(qp_audit, ROOT=ROOT, verify=verify, change=change, ACTIONS=ACTIONS, route=route, inspect=inspect):
        qp_audit.main()
