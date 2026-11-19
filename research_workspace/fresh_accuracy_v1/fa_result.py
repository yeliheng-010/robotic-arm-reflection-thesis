"""成功、已知失败、资格拒绝和未知采用互斥分母。"""
from fa_common import POLICIES


def classify(row, policy):
    if row['status'] in ('camera_rejected', 'geometry_rejected'):
        return 'rejected'
    audit = row.get('policies', {}).get(policy, {})
    if row['status'] != 'paired' or audit.get('passed') is not True:
        return 'unknown'
    success = audit.get('success')
    return 'success' if success is True else 'failure' if success is False else 'unknown'


def totals(rows):
    summary = {}
    for policy in POLICIES:
        counts = {key: 0 for key in ('success', 'failure', 'rejected', 'unknown')}
        for row in rows:
            counts[classify(row, policy)] += 1
        counts['registered'] = len(rows)
        counts['audited_executed'] = counts['success']+counts['failure']
        summary[policy] = counts
    return summary
