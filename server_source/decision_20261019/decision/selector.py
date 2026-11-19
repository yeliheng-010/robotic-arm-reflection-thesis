"""模型选择、确定性数值编译和审计明确标记为混合策略。"""
import json
from pathlib import Path
import urllib.request

from reflection.reflector import Reflection, stable_error
from training.refine.prompt import unique_object, reject_constant
from decision.candidates import build_candidates

SYSTEM = '''你是机器人控制候选的选择器。根据可观测错误、执行阶段、参数作用和历史，选择一个最能改善当前失败的候选。
输出且仅输出 JSON {"cause":"引用具体证据与候选作用的简短理由","choice":"候选id或abstain"}。
候选由外部数值程序根据测量生成，不代表已通过物理验证。只选择列表中的候选；不要自行生成或修改数值。
区分抓取、搬运、释放和全程结束后的验收。运动时间倍率只改变速度，不改变固定轨迹的空间路径。
last_completed_motion是验收之前最后完成的动作，并不证明故障在该动作中发生。残差XY是世界坐标，不是高度。
先判断候选能否作用于当前失败的阶段；再判断是否存在已失败的相同选择。不要把伴随现象当作已证实的原因。
现有证据无法支持任何有效候选时选择abstain。不要编造传感器反应、动态避障、未提供的图像或未来成功。'''


def build_request(instruction, report, *, parameters, source, history=()):
    choices = build_candidates(report, parameters, source=source)
    payload = {'instruction': instruction, 'carried_body': source, 'error': stable_error(report),
               'parameters': parameters.to_dict(), 'candidates': choices,
               'history': [{'error': stable_error(x['error']), 'reflection': x['reflection']} for x in history]}
    messages = [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
    return messages, choices


def parse_choice(raw, choices):
    answer = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(answer, dict) or set(answer) != {'cause', 'choice'}:
        raise ValueError('Expected exactly cause and choice')
    if not isinstance(answer['cause'], str) or not answer['cause'].strip():
        raise ValueError('Missing cause')
    chosen = next((x for x in choices if x['id'] == answer['choice']), None)
    if chosen is None:
        raise ValueError('Abstained or unknown candidate: ' + str(answer['choice']))
    return Reflection(answer['cause'], dict(chosen['changes']), 'hybrid_llm_selector')


def generate(messages, endpoint):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(endpoint + '/reflect',
        data=json.dumps({'messages': messages}, ensure_ascii=False).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with opener.open(request, timeout=240) as response:
            return json.load(response)
    except Exception as error:
        raise RuntimeError('Teacher request failed: ' + str(error)) from error


class HybridSelector:
    def __init__(self, instruction, *, source, endpoint, audit_path):
        self.instruction, self.source = instruction, source
        self.endpoint, self.audit_path = endpoint, Path(audit_path)

    def reflect(self, report, parameters, history=()):
        messages, choices = build_request(self.instruction, report.to_dict(),
            parameters=parameters, source=self.source, history=history)
        event = {'messages': messages, 'candidates': choices}
        try:
            event['response'] = generate(messages, self.endpoint)
            result = parse_choice(event['response']['text'], choices)
            parameters.updated(result.changes)
            event['compiled'] = result.to_dict()
            return result
        except (ValueError, RuntimeError) as error:
            event['error'] = str(error)
            raise
        finally:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_path.open('a') as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + '\n')

