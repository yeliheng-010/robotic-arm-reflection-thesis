"""明确分母、初始成功与四组配对方向，不把前缀当新预算。"""
import unittest
from am_common import METHODS
from am_metrics import trace_metrics,summarize


def metrics(success):
    return trace_metrics(dict(success=success,extra_observations=0,decisions=[],
        attempts=[dict(success=success)]))


class MetricsTests(unittest.TestCase):
    def test_all_pair_directions_and_skips(self):
        rows=[]
        for a,b in ((True,True),(False,False),(True,False),(False,True)):
            rows.append(dict(eligible=True,methods={m:metrics(s) for m,s in zip(METHODS,(a,b,a,b))}))
        rows.append(dict(eligible=False,methods={}))
        value=summarize(rows)
        self.assertEqual((5,4,1),(value['planned'],value['eligible'],value['skipped']))
        self.assertEqual({'both_success':1,'both_fail':1,'a_only':1,'b_only':1},
                         value['paired']['fixed_first__adaptive'])
        self.assertEqual(6,len(value['paired']))

    def test_initial_success_is_not_recovery(self):
        value=metrics(True)
        self.assertFalse(value['recovered'])
        self.assertEqual([True,True,True],value['cumulative_success'])

    def test_failed_early_stop_not_padded_with_attempts(self):
        value=metrics(False)
        self.assertEqual(1,value['attempts'])
        self.assertEqual([False,False,False],value['cumulative_success'])


if __name__=='__main__':
    unittest.main()
