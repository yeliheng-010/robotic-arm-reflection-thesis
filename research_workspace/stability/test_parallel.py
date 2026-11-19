"""多GPU调度只分配原任务编号，不能重复或改变数据身份。"""
import tempfile
from pathlib import Path
import unittest
from stability.parallel_state import lane_indices, topology, validate_plan


class ParallelTests(unittest.TestCase):
    def test_lanes_partition_without_missing_or_duplicate_tasks(self):
        lanes = [lane_indices(17, lane=i, lanes=4, completed={0, 7}) for i in range(4)]
        self.assertEqual(list(range(1, 7))+list(range(8, 17)), sorted(sum(lanes, [])))
        self.assertEqual([1, 5, 9, 13], lanes[1])

    def test_invalid_lane_rejected(self):
        for lane, count in ((4, 4), (-1, 4), (0, 0)):
            with self.assertRaises(ValueError):
                lane_indices(10, lane=lane, lanes=count, completed=set())

    def test_topology_matches_actual_scheduler_types(self):
        self.assertEqual(['v100', 'v100'], topology(2))
        self.assertEqual(['svc', 'svc', 'v100', 'v100'], topology(4))
        with self.assertRaises(ValueError):
            topology(3)

    def test_resume_does_not_skip_unfinished_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'tasks/00000').mkdir(parents=True)
            (root/'tasks/00000/summary.json').write_text('{}')
            (root/'tasks/00001/expert/run_000').mkdir(parents=True)
            self.assertEqual({0}, validate_plan(root, 3))
            (root/'tasks/99999').mkdir()
            (root/'tasks/99999/summary.json').write_text('{}')
            with self.assertRaises(ValueError):
                validate_plan(root, 3)


if __name__ == '__main__':
    unittest.main()
