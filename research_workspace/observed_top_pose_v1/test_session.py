import unittest
from unittest.mock import patch
import span_runtime
from span_runtime import SpanSession
from top_session import StrategySession
from top_runtime import filter_context


class SessionDispatchTests(unittest.TestCase):
    def test_both_strategies_dispatch_with_scoped_filter(self):
        session = StrategySession.__new__(StrategySession)
        session.state = dict(parameters=dict(grasp_offset=[0.,0.,0.]))
        original = span_runtime.filter_context
        seen = []
        with patch.object(SpanSession, '_engine', lambda self:seen.append(span_runtime.filter_context)):
            session.case = dict(strategy='original')
            session._engine()
            session.case = dict(strategy='observed_top')
            session._engine()
        self.assertEqual([original, filter_context], seen)
        self.assertIs(original, span_runtime.filter_context)
