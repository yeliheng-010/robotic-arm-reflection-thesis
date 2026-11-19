"""显式描述本执行器的能力边界；不增加修复回答或重试调用。"""
from pathlib import Path
from stability.prompt import build_messages
from flashnext.client import generate, append, parse_correction
from controlled.feedback import check_action
from controlled.config import MAX_TOKENS

CAPABILITIES = '''
本轮执行器能力约束（优先于上述通用参数说明）：
规划器使用固定动作序列，定位器使用固定仿真定位；replan、reground 不会改变它们，不能请求这两个动作。
仅选择 lift_height、time_scale、grasp_offset、place_offset、candidate_index 中有实际作用的修改。
候选索引还必须小于 diagnostics.available_candidate_count。不能原样重复当前参数。
反馈仅含本次展示的测量；缺失字段代表未知，不是零。simulated_measurement 表示有模拟测量误差。
错误类别和阶段仍来自理想检测器；不要猜测被隐藏的真实坐标。历史中的测量是当时的观测，不是新测量。
'''


def messages(instruction, report, *, parameters, history):
    previous = [{'error': r['error'], 'reflection': {k: r['reflection'][k]
                for k in ('cause', 'changes')}} for r in history]
    result = build_messages(instruction, report, parameters=parameters, history=previous)
    result[0]['content'] += CAPABILITIES
    return result


class ControlledFlash:
    def __init__(self, instruction, directory):
        self.instruction, self.path = instruction, Path(directory)/'requests.jsonl'

    def reflect(self, report, parameters, history=()):
        prompt = messages(self.instruction, report.to_dict(), parameters=parameters.to_dict(), history=history)
        event = generate(prompt, max_tokens=MAX_TOKENS)
        try:
            if 'error' in event:
                raise ValueError(event['error'])
            count = report.evidence['diagnostics'].get('available_candidate_count')
            answer = parse_correction(event['text'], parameters, candidate_count=count)
            check_action(answer, parameters, candidate_count=count)
            event['parsed'] = answer.to_dict()
            return answer
        except Exception as error:
            event['error'] = repr(error)
            raise RuntimeError('Controlled Flash reflection failed: '+str(error)) from error
        finally:
            append(self.path, event)
