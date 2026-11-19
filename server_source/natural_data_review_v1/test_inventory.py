import unittest
from unittest.mock import patch
import inventory


class InventoryTests(unittest.TestCase):
    def context(self):
        step = dict(index=1, success=False)
        branch = dict(ledger=dict(item=dict(source='Block', destination='Bin'), steps=[step]),
                      views=[dict(path='one'), dict(path='two')])
        first = dict(public=[dict(attempt=1)], private=[dict(state_sha256='state', clean_sha256='clean')])
        second = dict(public=[dict(attempt=1), dict(attempt=1)],
                      private=[dict(state_sha256='state', clean_sha256='clean')]*2)
        return branch, dict(one=first, two=second)

    def test_shared_state_and_extra_observation_do_not_inflate_count(self):
        branch, data = self.context()
        with patch.object(inventory, 'read', side_effect=lambda path: data[path]):
            first = inventory.snapshot(branch, dict(after_attempt=1))
            branch['views'] = [dict(path='two')]
            self.assertEqual(first, inventory.snapshot(branch, dict(after_attempt=1)))

    def test_different_task_not_merged(self):
        branch, data = self.context()
        with patch.object(inventory, 'read', side_effect=lambda path: data[path]):
            first = inventory.snapshot(branch, dict(after_attempt=1))
            branch['ledger']['item']['source'] = 'Capsule'
            self.assertNotEqual(first, inventory.snapshot(branch, dict(after_attempt=1)))

    def test_success_is_not_natural_failure(self):
        branch, _ = self.context()
        branch['ledger']['steps'][0]['success'] = True
        with self.assertRaises(AssertionError):
            inventory.snapshot(branch, dict(after_attempt=1))

    def test_digest_ignores_dictionary_key_order(self):
        self.assertEqual(inventory.digest(dict(a=1, b=2)), inventory.digest(dict(b=2, a=1)))


if __name__ == '__main__':
    unittest.main()
