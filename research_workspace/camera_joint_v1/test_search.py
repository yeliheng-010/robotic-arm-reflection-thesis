import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from camera_joint_v1 import search


def camera(config, boxes, index):
    return dict(position=[index, 0, 0], target=[0, 0, 1], fovy=60.)


class SearchTests(unittest.TestCase):
    def test_original_budget_is_exact_and_has_no_retry(self):
        with patch.object(search, 'global_camera', camera), patch.object(search, 'observation',
                return_value=(dict(accepted=False), False)):
            rows = search.run(None, None, config={}, boxes={}, method='original', cache={})
        self.assertEqual(256, len(rows))
        self.assertEqual(list(range(256)), [r['proposal_index'] for r in rows])

    def test_invalid_local_slots_still_consume_budget(self):
        proposed = [dict(camera=None, anchor_index=0, offset_index=i, delta=[], reason='invalid') for i in range(200)]
        with patch.object(search, 'global_camera', camera), patch.object(search, 'observation',
                return_value=(dict(accepted=False, gate={}), False)), patch.object(search, 'local', return_value=iter(proposed)):
            rows = search.run(None, None, config={}, boxes={}, method='joint', cache={})
        self.assertEqual(256, len(rows))
        self.assertEqual(128, sum(r['stage'] == 'local' for r in rows))

    def test_first_success_stops_search(self):
        with patch.object(search, 'global_camera', camera), patch.object(search, 'observation',
                side_effect=[(dict(accepted=False), False), (dict(accepted=True), False)]) as measured:
            rows = search.run(None, None, config={}, boxes={}, method='joint', cache={})
        self.assertEqual(2, len(rows))
        self.assertEqual(2, measured.call_count)

    def test_cache_reuses_only_identical_camera(self):
        cache = {}
        with patch.object(search, 'framed', return_value=dict(passed=True)), patch.object(search, 'evaluate',
                return_value=dict(accepted=False, marker=[])) as measured:
            first, old = search.observation(None, None, camera=camera({}, {}, 0), boxes={}, cache=cache)
            first['marker'].append('mutation')
            second, reused = search.observation(None, None, camera=camera({}, {}, 0), boxes={}, cache=cache)
        self.assertFalse(old)
        self.assertTrue(reused)
        self.assertEqual([], second['marker'])
        self.assertEqual(1, measured.call_count)


if __name__ == '__main__':
    unittest.main()
