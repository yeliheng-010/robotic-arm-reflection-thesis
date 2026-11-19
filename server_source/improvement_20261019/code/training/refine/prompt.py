"""只描述参数语义；不根据故障标签或规则生成修正答案。"""
import json

from reflection.reflector import Reflection
from training.qlora.data import make_messages as legacy_messages

FORMAT = 'text-reflection-v3-normalized-evidence'
SYSTEM = '''你是 UR5e 抓取搬运任务的故障分析器。仅根据提供的观测证据和历史尝试，选择下一次尝试的参数。
输出且仅输出一个 JSON 对象：{"cause":"基于证据的简短原因与预期作用","changes":{需要改变的参数:绝对新值}}。
可写参数只有：
- replan、reground：布尔值，分别请求重新规划、重新定位；不是直接改变机器人运动的参数。
- lift_height：抓起后、横向搬运前的竖直抬升距离，单位米，0.10 至 0.48。
- time_scale：运动持续时间倍率，0.5 至 3，数值越大运动越慢。
- grasp_offset、place_offset：分别加到抓取位置、释放位置上的世界坐标 XYZ 三维偏移，单位米，各分量 -0.25 至 0.25。
- candidate_index：已有候选的索引，整数 0 至 4；不能创造被过滤掉的候选。
closure、残差、contacts、diagnostics 是只读测量，不是可写参数。
grasp_residual_xy 的定义是实际指令抓取位置减去物体位置；placement_residual_xy 是最终物体位置减去目标中心。
向量顺序始终是 X、Y、Z。changes 是替换当前参数的绝对值，不是增量。用当前参数解释新值会让位置向哪个方向改变。
先确认失败发生在哪个运动段，以及证据是否支持所选参数的作用。小的非零残差不一定是主要原因。
只修改有证据支持的字段。不要原样重复已失败的参数或输出全部默认参数。不要编造测量、未来成功、注入故障或隐藏目标。
合法 JSON 与合法参数并不代表物理上必定可达。你没有图像，不能声称看到了未提供的内容。'''


def build_messages(instruction, report, *, parameters, history=()):
    messages = legacy_messages(instruction, report, parameters, history, {})[:-1]
    messages[0]['content'] = SYSTEM
    return messages


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON field: ' + key)
        value[key] = item
    return value


def reject_constant(value):
    raise ValueError('Nonfinite JSON number: ' + value)


def parse_response(raw, parameters):
    result = json.loads(raw.strip(), object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(result, dict) or set(result) != {'cause', 'changes'}:
        raise ValueError('Expected exactly cause and changes')
    if not isinstance(result['cause'], str) or not result['cause'].strip():
        raise ValueError('Missing cause')
    updated = parameters.updated(result['changes'])
    if updated == parameters:
        raise ValueError('Correction does not change any parameter')
    return Reflection(result['cause'], result['changes'], 'llm')

