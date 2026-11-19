import unittest
from hp_policy import allowed_initial


class HeldPolicyTests(unittest.TestCase):
    def setUp(self):
        self.support=dict(roots=['PurpleCapsule','world'],distance=-1e-6)

    def test_allows_only_existing_support_at_exact_start(self):
        self.assertTrue(allowed_initial(self.support,[self.support],first_sample=True))
        self.assertFalse(allowed_initial(self.support,[self.support],first_sample=False))

    def test_rejects_new_deeper_and_nonsupport_contacts(self):
        for row in (dict(roots=['PurpleCapsule','world'],distance=-2e-6),
                    dict(roots=['PurpleCapsule','RedBin'],distance=-1e-6),
                    dict(roots=['PurpleCapsule','ur5e_base'],distance=-1e-6)):
            self.assertFalse(allowed_initial(row,[self.support],first_sample=True))
        self.assertFalse(allowed_initial(self.support,[],first_sample=True))


if __name__=='__main__':
    unittest.main(verbosity=2)
