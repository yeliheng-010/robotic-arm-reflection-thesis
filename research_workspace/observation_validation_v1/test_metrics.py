"""预算前缀计费、跳过分母和配对种子组的统计边界。"""
import unittest
from budget_metrics import prefix,summarize,analyze
from pilot import scenes,SMOKE_SEEDS,SHARDS


def trace(outcomes):
    return dict(attempts=[dict(success=x) for x in outcomes],
        decisions=[dict(after_attempt=i,observation={'extra_cost':2 if i==1 else 0})
                   for i in range(1,len(outcomes))])


def row(name,seed,*,left,right,eligible=True):
    methods={} if not eligible else {
        'latest':{str(b):prefix(trace(left),b) for b in (1,2,3)},
        'median':{str(b):prefix(trace(right),b) for b in (1,2,3)}}
    return dict(id=name,seed=seed,eligible=eligible,methods=methods)


class MetricTests(unittest.TestCase):
    def test_budget_one_cannot_charge_future_observations(self):
        t=trace([False,False,True])
        self.assertEqual(dict(success=False,first_success=False,attempts=1,extra_observations=0),prefix(t,1))
        self.assertEqual(2,prefix(t,2)['extra_observations'])
        self.assertFalse(prefix(t,2)['success'])
        self.assertTrue(prefix(t,3)['success'])

    def test_early_success_not_padded_to_budget(self):
        self.assertEqual(1,prefix(trace([True]),3)['attempts'])
        self.assertEqual(0,prefix(trace([True]),3)['extra_observations'])

    def test_full_failure_stays_failure_at_all_budgets(self):
        t=trace([False,False,False])
        self.assertEqual([False,False,False],[prefix(t,b)['success'] for b in (1,2,3)])

    def test_both_directions_of_method_difference_retained(self):
        rows=[row('a',1,left=[False,False,True],right=[False,True]),
              row('b',1,left=[False,True],right=[False,False,True])]
        c=summarize(rows)[1]
        self.assertEqual({'median_only':1,'latest_only':1},c['paired'])
        self.assertEqual(1,c['methods']['latest']['successes'])
        self.assertEqual(1,c['methods']['median']['successes'])

    def test_skipped_conditions_not_observed_failures(self):
        rows=[row('a',1,left=[True],right=[True]),row('b',2,left=[],right=[],eligible=False)]
        c=summarize(rows)[0]
        self.assertEqual((2,1,1),(c['planned'],c['executed'],c['skipped']))
        self.assertEqual({'both_success':1},c['paired'])

    def test_shared_seed_pairs_not_independent_seeds(self):
        values=[dict(scene={'id':str(i),'seed':i//2,'source':'object'},eligible=False,trajectories=[])
                for i in range(4)]
        output=analyze(values,lambda _:None)
        self.assertEqual(2,output['independent_seed_groups'])
        self.assertEqual(4,len(output['rows']))
        self.assertEqual([1,2,3],output['preregistered_budgets'])

    def test_new_batch_balanced_after_smoke_reuse(self):
        rows=scenes()
        smoke=[r for r in rows if r['seed'] in SMOKE_SEEDS]
        self.assertEqual(4,len(smoke))
        for shard in range(SHARDS):
            assigned=rows[shard::SHARDS]
            self.assertEqual(6,len(assigned))
            self.assertEqual(5,sum(r['seed'] not in SMOKE_SEEDS for r in assigned))


if __name__=='__main__':
    unittest.main()
