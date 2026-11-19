"""只测试实时保护的阻断接线，不冒充几何或物理验证。"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np


def check_fixture(feasible):
    path=Path(__file__).with_name('held.py')
    tree=ast.parse(path.read_text(encoding='utf-8'))
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_and_run']
    saved=[]
    def abort(*args,**kwargs):
        raise RuntimeError('held guard rejected')
    scope=dict(np=np,sm=SimpleNamespace(SE3=lambda a:SimpleNamespace(A=a)),
        inspect=lambda *a,**k:dict(feasible=feasible),clone_robot=lambda r:r,
        robot_context=lambda r,e:{},plan_values=lambda legs:[],save=lambda p,v:saved.append(v),
        abort=abort,ErrorType=SimpleNamespace(COLLISION=1))
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec'),scope)
    return scope['check_and_run'],saved


class HeldTests(unittest.TestCase):
    def test_rejected_held_geometry_does_not_call_backend(self):
        check,saved=check_fixture(False)
        calls=[]
        with self.assertRaisesRegex(RuntimeError,'held guard rejected'):
            check(lambda *v:calls.append(v),(None,None,[1,2,3],[0,1,1,1],None,None),
                  trace=dict(selected=dict(pose=np.eye(4)),_surface_item={}),folder=Path('unused'))
        self.assertEqual([],calls)
        self.assertEqual(1,len(saved))

    def test_accepted_held_geometry_calls_backend_once(self):
        check,saved=check_fixture(True)
        calls=[]
        check(lambda *v:calls.append(v),(None,None,[1,2,3],[0,1,1,1],None,None),
              trace=dict(selected=dict(pose=np.eye(4)),_surface_item={}),folder=Path('unused'))
        self.assertEqual(1,len(calls))
        self.assertEqual(1,len(saved))
