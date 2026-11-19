"""动作语义自动判定；解释复核必须单独完成。"""
from reflection.reflector import Parameters
from controlled.feedback import check_action
from flashnext.client import parse_correction

VARIANT_CALLS = 48
TOLERANCE = 1e-8


def action_check(item, changes):
    try:
        Parameters().updated(item['parameters']).updated(changes)
    except (ValueError, TypeError) as error:
        return dict(passed=False, reason=str(error))
    if set(changes) & set(item['forbidden']):
        return dict(passed=False, reason='Parameter does not address observed failure stage')
    if item['expected'] is None:
        return dict(passed=True, reason='No numerical target; rationale needs review')
    actual = changes.get(item['target'])
    passed = set(changes) == {item['target']} and actual is not None
    passed = passed and all(abs(a-b) <= TOLERANCE for a,b in zip(actual,item['expected']))
    return dict(passed=bool(passed), expected=item['expected'], actual=actual,
                reason='Absolute measured compensation and minimal relevant change')


def evaluate(event, item):
    event.update(legal=False, rationale_review='pending', action_check={'passed':False})
    try:
        if 'error' in event:
            raise ValueError(event['error'])
        parameters = Parameters().updated(item['parameters'])
        count = item['report']['evidence']['diagnostics']['available_candidate_count']
        answer = parse_correction(event['text'], parameters, candidate_count=count)
        check_action(answer, parameters, candidate_count=count)
        event.update(legal=True, parsed=answer.to_dict(), action_check=action_check(item, answer.changes))
    except (ValueError, TypeError, KeyError) as error:
        event['validation_error'] = repr(error)


def gate(events):
    return len(events) == VARIANT_CALLS and all(
        e.get('legal') and e.get('action_check',{}).get('passed') and
        not e.get('service_error') and e.get('rationale_review') == 'passed' for e in events)
