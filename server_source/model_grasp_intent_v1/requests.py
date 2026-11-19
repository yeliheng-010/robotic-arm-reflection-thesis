"""规则与模型共享同一数值观测、动作和预算。"""
from copy import deepcopy
import json
from model_grasp_intent_v1.contract import CHOICES
from model_grasp_intent_v1.observations import public

SYSTEM = '''依据提供的观测自主选择下一步抓取意图；不要假定已知失败原因。
本接口仅规划，不执行运动；规划接受不等于任务成功。
局部x轴是向目标运动的接近轴，y轴是闭合轴；世界Z向上，单位米。
tilt_deg为与竖直向下的夹角；azimuth_deg为接近运动方向的水平投影，从世界+X朝+Y计角。
接近起点位于抓点减去接近轴的方向。顶抓tilt_deg=0时azimuth_deg必须为0。
region使用observed_top.long_axis，正负各移动min(20mm,观测长度20%)；depth_mm是顶面下深度。
symmetry_deg=180反转闭合轴。顶面估计可能偏差，侧抓也不保证可行。
非目标点云仅反映可见表面，未观测到点不代表没有障碍。不得修改安全门槛或预算。
只输出严格JSON：{"action":{"id":"合法动作ID","args":{}}}。'''


def build(raw, remaining, *, history, can_observe):
    actions = [dict(id='STOP', args_spec={})]
    if remaining['planning'] > 0:
        actions.insert(0, dict(id='PROPOSE_GRASP', args_spec=deepcopy(CHOICES)))
    if can_observe and remaining['observations'] > 0:
        actions.append(dict(id='OBSERVE', args_spec={}))
    return dict(version='model-grasp-intent-v1', phase='planning_only',
                observation=public(raw), budget=deepcopy(remaining), actions=actions,
                history=deepcopy(history))


def messages(request):
    return [dict(role='system', content=SYSTEM),
            dict(role='user', content=json.dumps(request, ensure_ascii=False, allow_nan=False))]
