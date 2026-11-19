"""恢复调度不覆盖失败阶段，且批量仍需新冒烟门槛。"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run as resumed


class ResumeTests(unittest.TestCase):
    def test_original_failed_status_preserved(self):
        old=resumed.ROOT/'stages/loop_smoke/shard_0/progress.json'
        before=old.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(resumed,'CONTROL',Path(folder)),patch.object(resumed,'verify_control'),\
                 patch.object(resumed,'entries',return_value=[(0,{'id':'unit'})]),\
                 patch.object(resumed,'execute',return_value={'id':'unit','service_errors':0}),\
                 patch('flashnext.client.ready',return_value={}),\
                 patch.dict(resumed.os.environ,{'SLURM_JOB_ID':'unit'}):
                resumed.run('loop_smoke',0)
            saved=json.loads((Path(folder)/'stages/loop_smoke/shard_0/progress.json').read_text())
            self.assertEqual('completed',saved['status'])
        self.assertEqual(before,old.read_bytes())

    def test_missing_new_gate_blocks_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(resumed,'CONTROL',Path(folder)),patch.object(resumed,'verify_control'):
                with self.assertRaises(FileNotFoundError):
                    resumed.run('batch',0)


if __name__=='__main__':
    unittest.main()
