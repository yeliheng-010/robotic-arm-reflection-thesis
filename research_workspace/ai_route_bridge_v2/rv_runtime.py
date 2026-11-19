from contextlib import contextmanager, ExitStack
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import goal_endpoints
import waypoint_search
import goal_audit_geometry
from cm_pose import poses
from candidate_runtime import context as candidate_context
from rb_runtime import RouteSession
from rv_common import save, sha


def ordered(nominal):
    rows = poses(nominal)
    return [r for r in rows if r['id'] != 'original']+[r for r in rows if r['id'] == 'original']


@contextmanager
def mode(control):
    assert set(control) == {'grasp_mode'} and control['grasp_mode'] in ('original', 'world_down')
    with ExitStack() as stack:
        if control['grasp_mode'] == 'world_down':
            for module in (goal_endpoints, waypoint_search, goal_audit_geometry):
                stack.enter_context(patch.object(module, 'poses', ordered))
        yield


class VerticalSession(RouteSession):
    def _engine(self):
        control = self.case['control']
        save(self.folder/'control.json', control)
        with mode(control):
            if self.state['parameters']['replan']:
                with candidate_context(self.case['config']):
                    super()._engine()
            else:
                super()._engine()

    def _record(self):
        path = self.folder/'execution/result.json'
        self.record = self.result['records'][0]
        self.step = dict(index=self.index, state=self.state, success=bool(self.result['success']),
            result_path=str(path), result_sha256=sha(path), session_path=str(self.folder), control=self.case['control'])
        save(self.folder/'step.json', self.step)
