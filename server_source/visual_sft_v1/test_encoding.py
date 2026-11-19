import unittest
from encoding import suffix_labels


class EncodingTests(unittest.TestCase):
    def test_mask_only_prompt_and_preserve_answer_eos(self):
        self.assertEqual([-100,-100,3,99],suffix_labels([1,2],[1,2,3,99]))

    def test_prefix_changes_rejected(self):
        with self.assertRaises(AssertionError):
            suffix_labels([1,2],[1,8,3,99])

    def test_empty_answer_rejected(self):
        with self.assertRaises(AssertionError):
            suffix_labels([1,2],[1,2])


if __name__ == '__main__':
    unittest.main()
