import unittest
from jg_policy import Budget, select, staged


class PolicyTests(unittest.TestCase):
    def test_original_is_unchanged_and_no_alternatives_evaluated(self):
        original = dict(q=[0],duration=1.5)
        def unused():
            raise AssertionError('Safe original must not expand')
            yield
        result = select(original,unused(),check=lambda x:True,budget=Budget(3),record=lambda x:None)
        self.assertIs(original,result)

    def test_selects_first_approved_and_records_rejections(self):
        events=[]
        budget=Budget(9)
        result=select(0,iter([1,2,3]),check=lambda x:x==2,budget=budget,record=events.append)
        self.assertEqual(2,result)
        self.assertEqual(3,budget.used)
        self.assertEqual([False,False,True],[x['accepted'] for x in events])

    def test_shared_budget_caps_all_prefixes(self):
        budget=Budget(2)
        events=[]
        for _ in range(2):
            result=select(0,iter(range(10)),check=lambda x:False,budget=budget,record=events.append)
            self.assertIsNone(result)
        self.assertEqual(2,budget.used)
        self.assertEqual(2,len(events))

    def test_guard_error_is_not_success(self):
        def broken(x):
            raise RuntimeError('guard missing')
        with self.assertRaises(RuntimeError):
            select(0,iter([]),check=broken,budget=Budget(3),record=lambda x:None)

    def test_selected_primary_never_calls_fallback(self):
        expected=dict(selected=dict(id='old'))
        def unused():
            raise AssertionError('Do not perturb successful primary')
        self.assertIs(expected,staged(lambda:expected,unused))

    def test_rejected_primary_uses_fallback(self):
        expected=dict(selected=dict(id='new'))
        self.assertIs(expected,staged(lambda:dict(selected=None),lambda:expected))


if __name__ == '__main__':
    unittest.main(verbosity=2)
