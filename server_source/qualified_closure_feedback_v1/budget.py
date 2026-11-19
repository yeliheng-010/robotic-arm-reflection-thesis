"""新预算排他预约；不复用或删除旧尝试claim。"""
from qualified_closure_feedback_v1.common import RUN, MAX_DECISIONS, read, save, sha, verify


def reserve(ordinal):
    verify()
    if type(ordinal) is not int or not 1 <= ordinal <= MAX_DECISIONS:
        raise ValueError('model_budget_exhausted')
    if ordinal > 1:
        prior = read(RUN / f'decision_{ordinal-1}/result.json')
        if prior['status'] != 'rejected':
            raise ValueError('previous_decision_is_terminal')
    folder = RUN / f'decision_{ordinal}'
    save(folder / 'model_claim.json', dict(ordinal=ordinal, consumed=1,
                                          request_sha256=sha(folder / 'request.json')))
