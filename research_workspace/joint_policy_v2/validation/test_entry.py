import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from cc_runtime import VisibleSession
from jv_runtime import GeneralSession
from jv_entry import Session


class EntryTests(unittest.TestCase):
    def check_entry(self, group, *, strategy, expected):
        session=object.__new__(Session)
        session.case=dict(config=dict(group=group),strategy=strategy)
        with patch.object(VisibleSession,'_engine',return_value='original') as original, \
             patch.object(GeneralSession,'_engine',return_value='generic') as generic:
            self.assertEqual(expected,session._engine())
            self.assertEqual(int(expected=='original'),original.call_count)
            self.assertEqual(int(expected=='generic'),generic.call_count)

    def test_baseline_uses_frozen_original_entry(self):
        for strategy in ('original','observed_top'):
            self.check_entry('baseline',strategy=strategy,expected='original')

    def test_varied_original_strategy_is_not_overridden(self):
        self.check_entry('varied_noisy',strategy='original',expected='original')

    def test_varied_observed_top_uses_generic_policy(self):
        self.check_entry('varied_noisy',strategy='observed_top',expected='generic')


if __name__ == '__main__':
    unittest.main(verbosity=2)
