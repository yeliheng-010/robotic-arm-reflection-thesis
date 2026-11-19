"""仅规划，不提供执行回调。"""
from copy import deepcopy
import json
from model_grasp_intent_v1.contract import validate_budget, validate_response, require
from model_grasp_intent_v1.geometry import propose
from model_grasp_intent_v1.observations import validate, fingerprint
from model_grasp_intent_v1.requests import build


class Session:
    def __init__(self, observation, budget, *, observe=None):
        self.raw, self.limits = validate(observation), validate_budget(budget)
        self.used = dict.fromkeys(self.limits, 0)
        self.observe, self.history, self.seen = observe, [], set()

    def remaining(self):
        return {key: self.limits[key]-self.used[key] for key in self.limits}

    def request(self):
        return build(self.raw, self.remaining(), history=self.history,
                     can_observe=self.observe is not None)

    def record(self, action, feedback):
        self.history.append(dict(revision=self.raw['revision'], action=deepcopy(action),
                                 feedback=dict(status=feedback)))

    def refresh(self):
        require(self.observe is not None and self.remaining()['observations'] > 0,
                'observation_unavailable')
        self.used['observations'] += 1
        latest = validate(self.observe())
        require(latest['revision'] == self.raw['revision']+1, 'stale_observation')
        self.raw = latest
        return 'observation_updated'

    def plan(self, action, planner):
        key = fingerprint(self.raw) + json.dumps(action, sort_keys=True)
        if key in self.seen:
            return 'duplicate_proposal'
        self.seen.add(key)
        self.used['planning'] += 1
        proposal = propose(self.raw['target_points'], self.raw['nominal'], action)
        if proposal['status'] == 'rejected':
            return 'geometry_rejected'
        # callback 的其他字段、私有碰撞对和异常文本绝不进入模型请求。
        result = planner(deepcopy(proposal))
        require(type(result) is dict, 'invalid_planner_result')
        states = dict(ready='plan_ready_unverified', rejected='plan_rejected',
                      exhausted='planner_budget_exhausted')
        require(result.get('status') in states, 'invalid_planner_status')
        return states[result['status']]

    def result(self, status):
        return dict(status=status, used=deepcopy(self.used), history=deepcopy(self.history),
                    task_success=None, physical_attempts=0, training_eligible=False,
                    full_path_verified=False)


def decide(session, policy):
    request = session.request()
    session.used['decisions'] += 1
    action = validate_response(policy(deepcopy(request)))
    require(action['id'] in {row['id'] for row in request['actions']}, 'unavailable_action')
    return action


def advance(session, action, planner):
    if action['id'] == 'OBSERVE':
        return session.refresh()
    return session.plan(action, planner)


def run(observation, policy, planner, *, budget, observe=None):
    session = Session(observation, budget, observe=observe)
    while session.remaining()['decisions'] > 0 and session.remaining()['planning'] > 0:
        try:
            action = decide(session, policy)
        except Exception:
            return session.result('policy_error')
        if action['id'] == 'STOP':
            session.record(action, 'policy_stop')
            return session.result('policy_stop')
        try:
            feedback = advance(session, action, planner)
        except Exception:
            status = 'observation_error' if action['id'] == 'OBSERVE' else 'planner_error'
            session.record(action, status)
            return session.result(status)
        session.record(action, feedback)
        if feedback == 'plan_ready_unverified':
            return session.result(feedback)
    status = 'planning_budget_exhausted' if session.remaining()['planning'] == 0 else 'decision_budget_exhausted'
    return session.result(status)
