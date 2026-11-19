from copy import deepcopy
from types import SimpleNamespace
import json
import unittest
from test_boundary import fixture
from nc_requests import build
from nc_rule import choose
from nc_state import Branch


def context():
    ledger, record = fixture()
    branch = Branch(ledger['item'], ledger['steps'][0])
    session = SimpleNamespace(record=record, recorder=SimpleNamespace(public=lambda: {'samples': []}))
    observations = [{'observed': {'source': {'status': 'visible_surface'}, 'destination': {'status': 'visible_surface'}}}]
    view = SimpleNamespace(sampler=SimpleNamespace(rows=observations))
    return branch, session, view


class RequestTests(unittest.TestCase):
    def test_hidden_cause_does_not_change_input_or_rule(self):
        branch, session, view = context()
        first = build(branch, session, view)
        session.record['error'] = {'error_type': 'SECRET_CAUSE'}
        branch.ledger['steps'][0]['feedback'] = {'message': 'SECRET_CAUSE'}
        second = build(branch, session, view)
        self.assertEqual(first, second)
        self.assertNotIn('SECRET_CAUSE', json.dumps(second))
        self.assertEqual(choose(first['request']), choose(second['request']))

    def test_rule_uses_only_missing_depth_and_fixed_time_sequence(self):
        branch, session, view = context()
        request = build(branch, session, view)['request']
        self.assertEqual({'id': 'SET_TIME_SCALE', 'args': {'value': 1.5}}, choose(request))
        view.sampler.rows[0]['observed']['source']['status'] = 'insufficient_visible_depth'
        self.assertEqual('OBSERVE', choose(build(branch, session, view)['request'])['id'])
        branch.extra = 2
        request = build(branch, session, view)['request']
        self.assertNotIn('OBSERVE', [a['id'] for a in request['actions']])

    def test_modes_share_user_input_and_snapshots_do_not_mutate(self):
        branch, session, view = context()
        value = build(branch, session, view)
        before = deepcopy(value)
        view.sampler.rows.append({'future': True})
        self.assertEqual(before, value)
        self.assertEqual(value['direct_messages'][1], value['diagnostic_messages'][1])


if __name__ == '__main__':
    unittest.main()
