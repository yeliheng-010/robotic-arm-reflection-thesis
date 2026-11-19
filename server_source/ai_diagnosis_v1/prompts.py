"""两种模型方法共享同一可见输入和动作权限，仅输出要求不同。"""
import json
from contracts import require

COMMON = '''你负责在有限预算内选择机械臂下一步动作。输入仅含明确列出的证据和合法动作。
命令不等于动作已完成，计划TCP不等于实测TCP；未附加观测不能当作测量缺失或零值。
只能选择actions中的ID并按已登记参数范围给出args。不得增加预算或修改安全保护。
模型提议仍须执行侧检查；动作列出不意味着已知会成功。没有足够证据时明确保留不确定性。
只输出严格JSON，不得添加代码围栏或额外字段。'''
DIRECT = '''输出格式：{"action":{"id":"合法动作ID","args":{}}}。'''
DIAGNOSTIC = '''输出action、assessment和expected_observation三个字段。
action格式为{"id":"合法动作ID","args":{}}。
assessment格式为{"hypotheses":[{"claim":"简短可检验假设","evidence_ids":["实际证据ID"]}],
"uncertainty":"证据不足或尚不能排除的情况"}。
hypotheses最多3项，证据不足可以为空；不能编造证据。expected_observation简述动作之后预期可观察到的变化。
每段文字最多240字符。只需简短结论和证据引用，不要求展开内部推理。'''


def messages(request, *, mode):
    require(mode in ('direct', 'diagnostic'), 'Unknown model mode')
    suffix = DIRECT if mode == 'direct' else DIAGNOSTIC
    return [dict(role='system', content=COMMON+'\n'+suffix),
            dict(role='user', content=json.dumps(request, ensure_ascii=False, allow_nan=False))]
