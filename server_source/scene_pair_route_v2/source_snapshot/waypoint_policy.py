"""只从已证实的规划拒绝继续；不读取案例编号。"""
from route_policy import eligible

RISES = (0., .10, .20, .30)
LIFTS = (.35, .45, .55)
ROUTES = ('direct', 'x_low', 'x_high', 'y_low', 'y_high',
          'low_low', 'low_high', 'high_low', 'high_high')
CORRIDOR_MARGIN_M = .15


def allowed(record, trace, destination):
    evidence = (record.get('error') or {}).get('evidence', {})
    return bool(evidence.get('route_planning_rejected') and trace.get('active')
                and trace.get('selected') is None and eligible(trace.get('feedback'), destination))
