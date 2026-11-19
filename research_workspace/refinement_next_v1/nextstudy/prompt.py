"""显式策略指导的提示；不修改原版本，不在解析后修复答案。"""
from refinement.client import messages as previous_messages

GUIDANCE = '''
以下是通用纠偏策略约定，请按证据作简短判断，直接返回 JSON，不输出反复推导：
1. 区分误差 e 与新参数 u_new。对当前相关的、已测得的 XY 残差：
grasp 残差=指令抓取点−物体点；placement 残差=最终物体点−容器中心。
正 X 残差表示对应点偏向世界坐标正 X，补偿应减小 X 指令；负值相反。
两个公式均为 u_new_xy = u_current_xy - e_xy，而不是直接输出 -e 或 u+e。
各轴超出 [-0.25,0.25] 时，在你提交的答案内限制到最近边界；后续应根据新反馈再次判断。
例如当前偏移0.08米、对应残差0.02米，新绝对偏移为0.06米；1米=1000毫米。
2. 有可靠且与失败相关的明显 XY 残差时优先修正该偏移，不先盲换候选或改变抬升高度。
仅修改相关参数，保持未测Z与其它参数；这是一阶修正假设，不保证物理成功。
3. 按实际失败阶段选择参数：抓取前失败不能由抓取后的lift_height直接解决；
尚未到达放置阶段时，不把历史或不适用的placement残差当成本次放置测量。
candidate_index只选抓取姿态；更大的time_scale更慢。
4. 没有测量时不得套公式或编造坐标。可作有界探索，但cause必须明确未知或假设，
不能断言缺失偏差的方向，也不能把未测夹持力/惯性当成确定根因。
5. cause仅简短说明可见证据和动作依据，不给未经验证的必然因果结论。
提交前核对绝对值、单位、方向、阶段、实际候选数和历史；不要无变化地重复参数。
'''


def messages(instruction, report, *, parameters, history, variant):
    if variant not in ('current', 'guided'):
        raise ValueError('Unknown variant')
    result = previous_messages(instruction, report, parameters=parameters,
                               history=history, variant='flash_new')
    if variant == 'guided':
        result[0]['content'] += GUIDANCE
    return result
