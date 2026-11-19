"""失败恢复以首次失败为分母，服务错误不混入无效回答。"""
from controlled.config import ARMS, GROUPS


def measures(rows):
    failures = sum(not r['first_success'] for r in rows)
    recovered = sum(r['success'] and not r['first_success'] for r in rows)
    return dict(tasks=len(rows), successes=sum(r['success'] for r in rows),
                success_rate=sum(r['success'] for r in rows)/len(rows) if rows else None,
                first_failures=failures, recoveries=recovered,
                recovery_rate=recovered/failures if failures else None,
                calls=sum(r['calls'] for r in rows), attempts=sum(r['attempts'] for r in rows),
                invalid_outputs=sum(r['invalid_outputs'] for r in rows),
                service_errors=sum(r['service_errors'] for r in rows),
                collision_attempts=sum(r.get('collision_attempts', 0) for r in rows),
                elapsed_s=sum(r['elapsed_s'] for r in rows))


def summarize(rows):
    return {group: {arm: measures([r for r in rows if r['arm'] == arm and r['task']['level'] == group])
                    for arm in ARMS} for group in GROUPS}


def paired_gains(rows):
    result = {}
    for group in GROUPS:
        selected = [r for r in rows if r['task']['level'] == group]
        retry = {r['case']: r for r in selected if r['arm'] == 'retry'}
        result[group] = {}
        for arm in ('rule', 'flash'):
            paired = [r for r in selected if r['arm'] == arm and r['case'] in retry]
            rescued = sum(r['success'] and not retry[r['case']]['success'] for r in paired)
            regressed = sum(not r['success'] and retry[r['case']]['success'] for r in paired)
            result[group][arm] = dict(pairs=len(paired), rescued=rescued, regressed=regressed,
                                      success_gain=(rescued-regressed)/len(paired) if paired else None)
    return result
