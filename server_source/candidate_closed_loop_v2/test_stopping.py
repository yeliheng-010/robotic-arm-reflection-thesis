import unittest
from stopping import finish_reason


class StoppingTests(unittest.TestCase):
    def test_model_eos_not_tokenizer_eos(self):
        self.assertEqual('stop',finish_reason(248044,eos_ids=248044,generated=22,budget=128))

    def test_multiple_generation_eos(self):
        self.assertEqual('stop',finish_reason(9,eos_ids=[8,9],generated=128,budget=128))

    def test_budget_exhaustion(self):
        self.assertEqual('length',finish_reason(7,eos_ids=[8,9],generated=128,budget=128))

    def test_unexplained_early_stop_is_error(self):
        with self.assertRaises(ValueError):
            finish_reason(7,eos_ids=[8,9],generated=22,budget=128)


if __name__=='__main__':
    unittest.main()
