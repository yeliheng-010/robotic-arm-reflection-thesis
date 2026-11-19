import tempfile
import unittest
from pathlib import Path
from cc_common import read, save, sha
from gate import claim


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.trial = Path(self.temp.name)
        self.source = self.trial/'source.txt'
        self.source.write_text('frozen')
        save(self.trial/'manifest.json', {'max_attempts': 1,
            'identities': {str(self.source): sha(self.source)}})
        save(self.trial/'preflight_result.json', {'passed': True})
        save(self.trial/'execution_manifest.json', {'max_physical_attempts': 1,
            'identities': {str(self.trial/'manifest.json'): sha(self.trial/'manifest.json'),
                str(self.trial/'preflight_result.json'): sha(self.trial/'preflight_result.json')}})

    def test_valid_claim_is_persisted_before_execution(self):
        claim(self.trial)
        self.assertTrue((self.trial/'attempt_claim.json').exists())
        record = read(self.trial/'attempt_claim.json')
        self.assertEqual(1, record['physical_attempt_budget_consumed'])
        self.assertFalse((self.trial/'cases').exists())

    def test_second_claim_is_rejected(self):
        claim(self.trial)
        with self.assertRaises(FileExistsError):
            claim(self.trial)

    def test_changed_frozen_source_is_rejected(self):
        self.source.write_text('changed')
        with self.assertRaises(ValueError):
            claim(self.trial)
        self.assertFalse((self.trial/'attempt_claim.json').exists())

    def test_changed_preflight_is_rejected(self):
        (self.trial/'preflight_result.json').write_text('{"passed":false}')
        with self.assertRaises(ValueError):
            claim(self.trial)
        self.assertFalse((self.trial/'attempt_claim.json').exists())

    def test_existing_case_is_rejected(self):
        (self.trial/'cases').mkdir()
        with self.assertRaises(AssertionError):
            claim(self.trial)

    def test_missing_execution_registration_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            claim(self.trial/'unregistered')


if __name__ == '__main__':
    unittest.main(verbosity=2)
