"""分支跨尝试总预算；额外观测不能随新尝试重置。"""
from copy import deepcopy
from nc_common import MAX_ATTEMPTS, MAX_OBSERVATIONS, MAX_DECISIONS


class Branch:
    def __init__(self, item, first):
        self.ledger = dict(item=deepcopy(item), steps=[deepcopy(first)])
        self.extra, self.decisions, self.history = 0, 0, []

    @property
    def remaining(self):
        return MAX_OBSERVATIONS-self.extra

    @property
    def terminal(self):
        return self.ledger['steps'][-1]['success'] or len(self.ledger['steps']) >= MAX_ATTEMPTS

    def decide(self):
        assert not self.terminal and self.decisions < MAX_DECISIONS
        self.decisions += 1

    def observe(self):
        assert not self.terminal and self.remaining > 0
        self.extra += 1

    def append(self, step):
        assert not self.terminal and step['index'] == len(self.ledger['steps'])+1
        self.ledger['steps'].append(deepcopy(step))

    def remember(self, action):
        self.history.append(dict(after_attempt=len(self.ledger['steps']), action=deepcopy(action)))
