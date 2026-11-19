"""首次成功无模型日志属于正常路径；真实调用缺少日志仍须拒绝。"""
from pathlib import Path
import tempfile
import unittest
from stability.loop_results import read_events


class ResultTests(unittest.TestCase):
    def test_first_success_requires_no_request_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                rows = read_events(Path(tmp), calls=0)
            except FileNotFoundError:
                self.fail('Zero model calls must not require a request log')
            self.assertEqual([], rows)

    def test_actual_call_without_log_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                read_events(Path(tmp), calls=1)

    def test_request_count_must_match_raw_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'requests.jsonl').write_text('{"arm":"base"}\n')
            self.assertEqual([{'arm': 'base'}], read_events(root, calls=1))
            with self.assertRaises(ValueError):
                read_events(root, calls=2)


if __name__ == '__main__':
    unittest.main()
