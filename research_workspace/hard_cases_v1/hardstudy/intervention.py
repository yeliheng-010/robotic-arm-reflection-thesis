"""故障只作用于规划偏移；真实调用轨迹保留在审计侧。"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
from diversity.scene import ScenarioFault
from loopstudy.episode import attempt as base_attempt
from semanticfix2.protocol import sha
from stability.collection_status import atomic
from hardstudy.bridge import bound
from hardstudy.design import configuration


def expected(item,enabled):
    if enabled:
        return deepcopy(item['injection'])
    return dict(grasp=[0.,0.,0.],place=[0.,0.,0.],collision=False)


@contextmanager
def capture(item,*,enabled=True):
    values=expected(item,enabled)
    trace=dict(grasp=[],place=[])
    def reader(key):
        def read(fault):
            value=list(values[key])
            trace[key].append(value)
            return list(value)
        return read
    with patch.object(ScenarioFault,'grasp_bias',reader('grasp')),patch.object(
            ScenarioFault,'place_bias',reader('place')):
        yield trace


def attempt(item,state,*,directory,index,enabled=True):
    with bound(item,enabled=enabled),capture(item,enabled=enabled) as trace:
        step=base_attempt(item,state,directory=directory,index=index)
    path=Path(step['result_path'])
    raw=json.loads(path.read_text())
    raw['intervention']=dict(enabled=enabled,specification=expected(item,enabled),calls=trace,
        evaluator_modified=False,mechanism='explicit_planner_bias_and_divider')
    raw['scenario_config']=configuration(item)
    atomic(path,raw)
    step['intervention_enabled']=enabled
    step['result_sha256']=sha(path)
    return step


def audit(step,item,*,enabled=True):
    raw=json.loads(Path(step['result_path']).read_text())
    trace=raw['intervention']
    assert step['intervention_enabled']==enabled and trace['enabled']==enabled
    assert trace['specification']==expected(item,enabled) and trace['evaluator_modified'] is False
    assert raw['scenario_config']==configuration(item)
    for key in ('grasp','place'):
        assert all(value==expected(item,enabled)[key] for value in trace['calls'][key])
    assert trace['calls']['grasp'], 'No observed grasp-bias access; cannot verify intervention'
    if raw['success']:
        assert trace['calls']['place'], 'Successful placement without observed place-bias access'
