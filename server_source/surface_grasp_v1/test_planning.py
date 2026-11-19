"""真实 inspect 函数的接线测试；后端为替身，不是 MuJoCo 证明。"""
import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import numpy as np


def harness(fail=False):
    path=Path(__file__).with_name('planning.py')
    parsed=ast.parse(path.read_text(encoding='utf-8'))
    body=[node for node in parsed.body if isinstance(node,ast.FunctionDef) and node.name=='inspect']
    goals=SimpleNamespace(LIFTS=(.1,.2,.3))
    seen={}
    def observe(points,trace):
        trace['poses']=[{}]
        return nullcontext()
    def generate(row,points,called):
        called.append(True)
        return None
    def search(flow,case,events):
        seen['lifts']=goals.LIFTS
        if fail:
            raise RuntimeError('backend failure')
        return dict(selected={})
    scope=dict(np=np,PROJECT=Path('.'),read=lambda p:dict(target_points=[[0,0,0]]),
        opened=lambda m:nullcontext(object()),observation=observe,deadline=lambda s:nullcontext(),
        generator=generate,stage=lambda g,run:run(),search=search,save=lambda p,v:None,
        patch=patch,goal_search=goals)
    exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),scope)
    manifest=dict(planning_timeout_s=120,case=dict(state=dict(parameters=dict(lift_height=.2))))
    return scope['inspect'],manifest,goals,seen


class PlanningTests(TestCase):
    def test_only_registered_lift_is_searched_and_restored(self):
        inspect,manifest,goals,seen=harness()
        self.assertEqual(dict(status='ready'),inspect({},manifest,Path('unused')))
        self.assertEqual((.2,),seen['lifts'])
        self.assertEqual((.1,.2,.3),goals.LIFTS)

    def test_lift_context_restored_on_backend_failure(self):
        inspect,manifest,goals,seen=harness(fail=True)
        with self.assertRaisesRegex(RuntimeError,'backend failure'):
            inspect({},manifest,Path('unused'))
        self.assertEqual((.2,),seen['lifts'])
        self.assertEqual((.1,.2,.3),goals.LIFTS)
