"""共享首次默认观测的引用，分支补看仍真实渲染同一暂停环境。"""
from copy import deepcopy
from live_observations import Sampler
from live_budget import ObservationBudget


class View:
    def __init__(self, session, *, folder, remaining, shared=None):
        self.sampler = Sampler(session.lease.env, session.case['config'], item=session.case['item'],
            folder=folder, attempt=session.index, success=session.step['success'])
        self.sampler.budget = ObservationBudget(attempt=session.index, success=session.step['success'], limit=remaining)
        self.paths = []
        if shared is not None:
            self.sampler.rows = deepcopy(shared.sampler.rows[:1])
            self.sampler.private = deepcopy(shared.sampler.private[:1])
            self.sampler.budget.count = 1
            self.paths = shared.paths[:1]
        else:
            self.capture()

    def capture(self):
        row = self.sampler.capture()
        self.paths.append(str(self.sampler.folder/f"observation_{row['observation_index']}"))
        return row

    def summary(self):
        return dict(public=self.sampler.rows, private=self.sampler.private, paths=self.paths,
                    remaining=self.sampler.budget.remaining)
