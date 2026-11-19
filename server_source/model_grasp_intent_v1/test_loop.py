import unittest
from copy import deepcopy
from model_grasp_intent_v1.loop import run
from model_grasp_intent_v1.test_contract import intent
from model_grasp_intent_v1.test_geometry import points


def observation():
    return dict(qualified=True, revision=0, target_points=points().tolist(),
                scene_points=[[.7, .3, .75]], nominal=[.8, .4, .76])


def limits():
    return dict(decisions=4, planning=2, observations=1)


class LoopTests(unittest.TestCase):
    def test_rejected_plan_is_feedback_not_an_execution(self):
        requests, plans = [], []
        def policy(request):
            requests.append(deepcopy(request))
            return dict(action=intent(depth_mm=30 if len(requests)==1 else 15))
        def planner(proposal):
            plans.append(proposal)
            return dict(status='rejected', contacts=['PRIVATE_PAIR'], reason='PRIVATE_CAUSE')
        result = run(observation(), policy, planner, budget=limits())
        self.assertEqual(2, len(plans))
        self.assertEqual(0, result['physical_attempts'])
        self.assertEqual('planning_budget_exhausted', result['status'])
        self.assertNotIn('PRIVATE', str(requests))
        self.assertEqual('plan_rejected', requests[1]['history'][0]['feedback']['status'])

    def test_plan_ready_is_not_success(self):
        result = run(observation(), lambda _: dict(action=intent()),
                     lambda _: dict(status='ready'), budget=limits())
        self.assertEqual('plan_ready_unverified', result['status'])
        self.assertIsNone(result['task_success'])
        self.assertFalse(result['training_eligible'])

    def test_exception_consumes_budget_and_does_not_leak(self):
        def planner(_):
            raise RuntimeError('PRIVATE collision pair')
        result = run(observation(), lambda _: dict(action=intent()), planner, budget=limits())
        self.assertEqual(1, result['used']['planning'])
        self.assertEqual('planner_error', result['status'])
        self.assertNotIn('PRIVATE', str(result))

    def test_unqualified_input_stops_before_policy(self):
        raw = observation()
        raw['qualified'] = False
        with self.assertRaises(ValueError):
            run(raw, lambda _: self.fail('policy called'), None, budget=limits())

    def test_observe_does_not_reset_planning_budget(self):
        actions = iter([intent(), dict(id='OBSERVE', args={}), intent(depth_mm=15)])
        refreshed = observation()
        refreshed['revision'] = 1
        result = run(observation(), lambda _: dict(action=next(actions)),
                     lambda _: dict(status='rejected'), budget=limits(), observe=lambda: refreshed)
        self.assertEqual(dict(decisions=3, planning=2, observations=1), result['used'])

    def test_identical_retry_does_not_call_planner_twice(self):
        calls = []
        def planner(value):
            calls.append(value)
            return dict(status='rejected')
        result = run(observation(), lambda _: dict(action=intent()), planner, budget=limits())
        self.assertEqual(1, len(calls))
        self.assertEqual(4, result['used']['decisions'])

    def test_private_fields_in_observation_rejected(self):
        raw = observation()
        raw['collision_pairs'] = ['private']
        with self.assertRaises(ValueError):
            run(raw, None, None, budget=limits())

    def test_observation_error_consumes_budget_without_private_text(self):
        def observe():
            raise RuntimeError('PRIVATE truth')
        result = run(observation(), lambda _: dict(action=dict(id='OBSERVE', args={})),
                     None, budget=limits(), observe=observe)
        self.assertEqual(1, result['used']['observations'])
        self.assertEqual('observation_error', result['status'])
        self.assertNotIn('PRIVATE', str(result))

    def test_invalid_policy_never_calls_planner(self):
        result = run(observation(), lambda _: dict(action=intent(disable_collision=True)),
                     lambda _: self.fail('planner called'), budget=limits())
        self.assertEqual('policy_error', result['status'])
        self.assertEqual(1, result['used']['decisions'])
        self.assertEqual(0, result['used']['planning'])

    def test_request_mutation_cannot_reset_controller_budget(self):
        def policy(request):
            request['budget']['planning'] = 100
            request['history'].clear()
            return dict(action=intent())
        result = run(observation(), policy, lambda _: dict(status='rejected'), budget=limits())
        self.assertEqual(4, result['used']['decisions'])
        self.assertEqual(1, result['used']['planning'])
        self.assertEqual(4, len(result['history']))

    def test_same_cloud_with_new_revision_cannot_repeat_consumed_plan(self):
        actions = iter([intent(), dict(id='OBSERVE', args={}), intent(), dict(id='STOP', args={})])
        latest, calls = observation(), []
        latest['revision'] = 1
        def planner(proposal):
            calls.append(proposal)
            return dict(status='rejected')
        result = run(observation(), lambda _: dict(action=next(actions)), planner,
                     budget=limits(), observe=lambda: latest)
        self.assertEqual(1, len(calls))
        self.assertEqual('duplicate_proposal', result['history'][2]['feedback']['status'])

    def test_negative_and_boolean_budgets_rejected(self):
        for value in (-1, True, 9):
            budget = limits()
            budget['decisions'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                run(observation(), None, None, budget=budget)
