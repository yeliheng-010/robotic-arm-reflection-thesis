import unittest
from waypoint_policy import allowed


class PolicyTests(unittest.TestCase):
    def test_prior_rejection_with_target_contact_provenance(self):
        raw = dict(error={'evidence': {'route_planning_rejected': True}})
        trace = dict(active=True, selected=None, feedback=dict(error_type='collision',
                     evidence={'contacts': [['ur5e_base','BlueBin']]}))
        self.assertTrue(allowed(raw, trace, 'BlueBin'))

    def test_missing_or_unrelated_evidence_does_not_activate(self):
        raw = dict(error={'evidence': {'route_planning_rejected': True}})
        for trace in ({}, dict(active=False), dict(active=True, selected=None),
                      dict(active=True, selected={'id':'executed'})):
            self.assertFalse(allowed(raw, trace, 'BlueBin'))
        self.assertFalse(allowed(dict(error=None), {}, 'BlueBin'))


if __name__ == '__main__':
    unittest.main()
