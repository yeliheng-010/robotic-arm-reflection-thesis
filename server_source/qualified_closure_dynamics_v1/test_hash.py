"""大文件来源哈希必须有界读取，避免冻结模型权重时OOM。"""
import hashlib
import unittest
from unittest.mock import MagicMock, patch
from qualified_closure_dynamics_v1 import protocol


class HashTests(unittest.TestCase):
    def test_streaming_hash_uses_bounded_reads(self):
        calls = []
        blocks = iter([b'first', b'second', b''])
        def bounded(size=-1):
            self.assertGreater(size, 0)
            self.assertLessEqual(size, 1024 * 1024)
            calls.append(size)
            return next(blocks)
        fake = MagicMock()
        fake.read_bytes.side_effect = AssertionError('Unbounded whole-file read')
        fake.open.return_value.__enter__.return_value.read.side_effect = bounded
        with patch.object(protocol, 'Path', return_value=fake):
            digest = protocol.sha('large-source')
        self.assertEqual(hashlib.sha256(b'firstsecond').hexdigest(), digest)
        self.assertEqual(3, len(calls))


if __name__ == '__main__':
    unittest.main(verbosity=2)
