"""另进程重建初态并检查选中路径，再比较完整任务静态计划。"""
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from cp_probe import inspect
from cp_common import current
from js_geometry import EdgeChecker
from js_scope import context
from js_common import ROOT, RUN, NAME, inputs, read, save, sha, verify


def audit_edges(selection):
    case, previous = inputs()
    checks = []
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']):
        checker = EdgeChecker(rebuild(case,previous),case)
        for start,goal in zip(selection['path'],selection['path'][1:]):
            assert checker(start,goal), checker.last
            checks.append(checker.last)
    return checks


def main(mode):
    assert mode in ('full','audit')
    verify(RUN/'manifest.json')
    result = verify(RUN/'result.json')
    if result['selected'] is None:
        save(ROOT/(mode+'_skipped.json'),dict(reason='no_selected_pregrasp_path',physical_attempts=0))
        return
    checks = audit_edges(result['selected'])
    save(ROOT/mode/'edges.json',checks)
    with context(result['selected']):
        plan, trace = inspect(current(NAME))
    save(ROOT/mode/'plan.json',plan)
    save(ROOT/mode/'trace.json',trace)
    if mode == 'audit':
        assert plan == read(ROOT/'full/plan.json')
        assert trace == read(ROOT/'full/trace.json')
        assert checks == read(ROOT/'full/edges.json')
    verify(RUN/'manifest.json')
    save(ROOT/mode/'result.json',dict(passed=True,qualified=plan['selected'] is not None,
        independent=mode=='audit',selected=plan['selected'],status=plan['status'],
        checked_edges=len(checks),physical_attempts=0,model_calls=0,
        identities={str(p):sha(p) for p in (ROOT/mode).glob('*.json')}))
    print(dict(mode=mode,status=plan['status'],qualified=plan['selected'] is not None),flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
