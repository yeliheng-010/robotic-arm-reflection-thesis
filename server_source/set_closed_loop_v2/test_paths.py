"""继承协议的相对文件须绑定真实来源，不依赖当前工作目录。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import freeze
from common import sha


class SourcePathTests(unittest.TestCase):
    def test_noise_relative_code_resolves_to_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/'noise_feedback_v1/run.py'
            source.parent.mkdir()
            source.write_text('original noise implementation')
            protocol={'noise_source': {'code': {'run.py': sha(source)}}}
            with patch.object(freeze,'PARENT',root):
                self.assertEqual([str(source)],freeze.parent_code(protocol))

    def test_unknown_relative_source_is_rejected(self):
        with self.assertRaises(AssertionError):
            freeze.parent_code({'unknown': {'code': {'run.py': '0'*64}}})


if __name__ == '__main__':
    unittest.main()
