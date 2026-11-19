"""跨模型冒烟结果复用时，审计的临时全局替换不得并发。"""
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import run
from common import save


class ReuseTests(unittest.TestCase):
    def test_reused_model_audits_do_not_overlap(self):
        active, peak = 0, 0
        guard = threading.Lock()

        def slow_audit(result, entry):
            nonlocal active, peak
            with guard:
                active += 1
                peak = max(peak, active)
            time.sleep(0.05)
            with guard:
                active -= 1
            return {'passed': True}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pairs = [(i, {'uid': method, 'method': method})
                     for i, method in enumerate(('previous159', 'new189'))]
            for _, entry in pairs:
                folder = root/'tasks'/entry['uid']
                save(folder/'summary.json', {'executed': True, 'audit': {'passed': True}})
                save(folder/'result.json', {})
            with patch.object(run, 'ROOT', root), patch.object(run, 'audit', slow_audit):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    list(pool.map(run.execute, pairs))
        self.assertEqual(1, peak)


if __name__ == '__main__':
    unittest.main()
