import json
import tempfile
import unittest
from pathlib import Path
from f_common import sha
from observation_reference_v5 import observation


class ObservationReference(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.step = dict(index=2, session_path=str(self.root/'attempt_2'))
        self.path = self.root/'views/a2_o0.json'
        self.path.parent.mkdir()
        self.summary = dict(public=[dict(attempt=2)], private=[dict(calibration=True)],
            paths=[str(self.root/'observations/attempt_2/observation_0')])
        self.write(self.path, self.summary)
        self.result = dict(ledger=dict(steps=[self.step]),
            views=[dict(path=str(self.path), sha256=sha(self.path))])
        self.write(self.root/'result.json', self.result)

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def test_branch_reference(self):
        self.assertEqual(self.summary, observation(self.step))

    def test_hash_tampering(self):
        self.write(self.path, dict(self.summary, changed=True))
        with self.assertRaisesRegex(AssertionError, 'hash'):
            observation(self.step)

    def test_wrong_attempt(self):
        with self.assertRaisesRegex(AssertionError, 'ledger'):
            observation(dict(self.step, index=3))

    def test_foreign_frame(self):
        self.summary['paths'] = [str(self.root/'observations/attempt_3/observation_0')]
        self.write(self.path, self.summary)
        self.result['views'][0]['sha256'] = sha(self.path)
        self.write(self.root/'result.json', self.result)
        with self.assertRaises(AssertionError):
            observation(self.step)


if __name__ == '__main__':
    unittest.main()
