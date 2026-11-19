import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from surface_physical_v1.scope import COLLECTING,collection


def factory_fixture():
    path=Path(__file__).with_name('held.py')
    tree=ast.parse(path.read_text(encoding='utf-8'))
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='factory']
    calls=[]
    grasp=SimpleNamespace(_run_planners=lambda *a:calls.append('backend'))
    def checked(backend,values,*,trace,folder):
        calls.append('guard')
        return backend(*values)
    scope=dict(COLLECTING=COLLECTING,patch=patch,grasp=grasp,check_and_run=checked)
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec'),scope)
    original_factory=lambda original,trace:lambda *a,**k:grasp._run_planners(*a)
    wrapped=scope['factory'](original_factory,folder=Path('unused'))(None,{})
    return wrapped,calls


class WiringTests(unittest.TestCase):
    def test_collection_context_restored_on_error(self):
        def fail():
            self.assertTrue(COLLECTING.get())
            raise RuntimeError('collection error')
        with self.assertRaisesRegex(RuntimeError,'collection error'):
            collection(fail)()
        self.assertFalse(COLLECTING.get())

    def test_collection_skips_execution_guard_but_live_call_uses_it(self):
        wrapped,calls=factory_fixture()
        collection(wrapped)(1,2,3)
        self.assertEqual(['backend'],calls)
        calls.clear()
        wrapped(1,2,3)
        self.assertEqual(['guard','backend'],calls)
