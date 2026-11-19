"""旧提示原样保留；新提示仅追加参数语义，不注入逐例答案。"""
from pathlib import Path
from controlled.client import messages as original_messages
from controlled.config import MAX_TOKENS
from controlled.feedback import check_action
from flashnext.client import generate, append, parse_correction

SEMANTICS = '''
参数语义与提交前自检：
grasp_residual_xy = commanded grasp xy - object xy；placement_residual_xy = final object xy - container centre xy。
两种残差的对象不同，请根据定义检查拟议位移的方向，不要颠倒相减顺序。全部长度单位为米。
changes 中是参数的新绝对值，不是增量；实际变化是新值减当前值。
time_scale 是动作时长倍率：数值增大表示用时更长、运动更慢；减小表示更快。
candidate_index 只选择抓取姿态，不是放置候选；place_offset 才改变释放目标。
lift_height 只作用于抓取后的抬升，不能改变之前的 approach/grasp 路径。
缺失测量表示未知，不能当作零或编造坐标。若探索，明确说明依据不足。
输出前逐项自检：方向、阶段作用、取值边界、实际候选数量，以及相对当前参数是否有变化。
grasp_offset/place_offset 每轴 [-0.25,0.25]；lift_height [0.10,0.48]；time_scale [0.5,3]。
检查历史中的动作与结果；不重复无变化的动作。只输出要求的 JSON。
'''


def messages(instruction, report, *, parameters, history, variant):
    if variant not in ('flash_old', 'flash_new'):
        raise ValueError('Unknown prompt variant')
    result = original_messages(instruction, report, parameters=parameters, history=history)
    if variant == 'flash_new':
        result[0]['content'] += SEMANTICS
    return result


class SemanticFlash:
    def __init__(self, instruction, directory, *, variant):
        self.instruction, self.path = instruction, Path(directory)/'requests.jsonl'
        self.variant = variant

    def reflect(self, report, parameters, history=()):
        prompt = messages(self.instruction, report.to_dict(), parameters=parameters.to_dict(),
                          history=history, variant=self.variant)
        event = generate(prompt, max_tokens=MAX_TOKENS)
        event['variant'] = self.variant
        try:
            if 'error' in event:
                raise ValueError(event['error'])
            count = report.evidence.get('diagnostics', {}).get('available_candidate_count')
            answer = parse_correction(event['text'], parameters, candidate_count=count)
            check_action(answer, parameters, candidate_count=count)
            event['parsed'] = answer.to_dict()
            return answer
        except (ValueError, KeyError, TypeError) as error:
            event['error'] = repr(error)
            raise RuntimeError('Semantic Flash reflection failed: '+str(error)) from error
        finally:
            append(self.path, event)
