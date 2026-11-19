import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest


def subject(original):
    path=Path(__file__).with_name('capture.py')
    tree=ast.parse(path.read_text(encoding='utf-8'))
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
    scope=dict(patch=patch,raw_render=lambda env:'raw',original_checkpoint=original)
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec'),scope)
    return scope['checkpoint']


class CaptureTests(unittest.TestCase):
    def test_calibration_does_not_use_task_noise_stream(self):
        calls=[]
        env=SimpleNamespace(render=lambda:calls.append('noise'))
        original=env.render
        fn=subject(lambda e,c,**k:e.render())
        self.assertEqual('raw',fn(env,{},folder=None,phase='preflight'))
        self.assertEqual([],calls)
        self.assertIs(original,env.render)

    def test_original_renderer_restored_on_failure(self):
        env=SimpleNamespace(render=lambda:'noise')
        original=env.render
        def fail(e,c,**kwargs):
            self.assertEqual('raw',e.render())
            raise RuntimeError('capture failure')
        with self.assertRaisesRegex(RuntimeError,'capture failure'):
            subject(fail)(env,{},folder=None,phase='preflight')
        self.assertIs(original,env.render)
