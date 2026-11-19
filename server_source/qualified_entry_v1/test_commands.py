"""无需本地MuJoCo，验证命令核对会拒绝高度、时长、阶段变化。"""
import ast
from pathlib import Path
import unittest
import numpy as np


def comparator():
    path = Path(__file__).with_name('commands.py')
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'compare']
    scope = dict(np=np, plan_values=lambda rows: rows, NUMERIC_ATOL=1e-12)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope['compare']


class CommandTests(unittest.TestCase):
    def test_identical_commands_accepted(self):
        row = dict(phase='descent', duration=1.5, samples=[[0., 0., 1.]])
        self.assertTrue(comparator()([row], [row])['passed'])

    def test_changed_height_rejected(self):
        a = dict(phase='descent', duration=1.5, samples=[[0., 0., 1.]])
        b = dict(a, samples=[[0., 0., 1.08]])
        with self.assertRaises(AssertionError):
            comparator()([a], [b])

    def test_changed_duration_or_phase_rejected(self):
        a = dict(phase='descent', duration=1.5, samples=[[0., 0., 1.]])
        for b in (dict(a, duration=1.), dict(a, phase='transport')):
            with self.assertRaises(AssertionError):
                comparator()([a], [b])


if __name__ == '__main__':
    unittest.main()
