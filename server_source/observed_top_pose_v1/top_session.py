from contextlib import nullcontext
from unittest.mock import patch
import nc_session
from span_runtime import SpanSession
from top_runtime import TopSession
from top_motion import context
from f_common import save, sha

STRATEGIES = ('original', 'observed_top')


class StrategySession(TopSession):
    def execute(self):
        strategy = self.case['strategy']
        assert strategy in STRATEGIES
        scope = patch.object(nc_session, 'motion_context', context) if strategy == 'observed_top' else nullcontext()
        with scope:
            super().execute()

    def _engine(self):
        if self.case['strategy'] == 'observed_top':
            super()._engine()
        else:
            SpanSession._engine(self)

    def _record(self):
        path = self.folder/'execution/result.json'
        self.record = self.result['records'][0]
        self.step = dict(index=self.index, state=self.state, success=bool(self.result['success']),
            result_path=str(path), result_sha256=sha(path), session_path=str(self.folder),
            control=self.case['control'], strategy=self.case['strategy'])
        save(self.folder/'step.json', self.step)
