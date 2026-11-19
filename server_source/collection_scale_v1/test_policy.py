import unittest
from sc_policy import next_step, shard_cases


def history(count, types=('SET_GRASP_STRATEGY',), recoveries=1):
    return [dict(batch=i,snapshots=3,recoveries=recoveries,action_types=list(types),tasks=['block','capsule'])
        for i in range(count)]


class ScaleTests(unittest.TestCase):
    def test_three_single_task_batches_require_review(self):
        rows = history(3,types=('SET_GRASP_STRATEGY','SET_TIME_SCALE'))
        for row in rows:
            row['tasks'] = ['block']
        self.assertFalse(next_step(rows,quantitative_ready=False)['advance'])

    def test_three_single_action_batches_do_not_trigger_blind_expansion(self):
        self.assertFalse(next_step(history(3),quantitative_ready=False)['advance'])

    def test_ready_gate_stops_new_collection(self):
        self.assertFalse(next_step(history(1),quantitative_ready=True)['advance'])

    def test_insufficient_but_informative_collection_continues(self):
        self.assertTrue(next_step(history(3,types=('SET_GRASP_STRATEGY','SET_TIME_SCALE')),
            quantitative_ready=False)['advance'])

    def test_same_seed_never_shared_by_shards(self):
        cases = [dict(item=dict(seed=i,task=t)) for i in range(8) for t in (0,1)]
        shards = [shard_cases(cases,index=i) for i in range(4)]
        self.assertEqual(16,sum(map(len,shards)))
        for i,left in enumerate(shards):
            for right in shards[i+1:]:
                self.assertFalse({c['item']['seed'] for c in left}&{c['item']['seed'] for c in right})


if __name__ == '__main__':
    unittest.main()
