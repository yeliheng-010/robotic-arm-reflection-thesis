"""真实观测与执行权限只由控制器账本授予。"""


class ObservationBudget:
    def __init__(self, *, attempt, success, limit=2):
        if type(attempt) is not int or not 1 <= attempt <= 3 or type(success) is not bool:
            raise ValueError('Invalid attempt outcome')
        if type(limit) is not int or not 0 <= limit <= 2:
            raise ValueError('Invalid observation limit')
        self.attempt, self.success, self.limit = attempt, success, limit
        self.count = 0

    @property
    def remaining(self):
        return max(0, self.limit - max(0, self.count - 1))

    def reserve(self):
        if self.count and (self.success or self.attempt == 3 or self.remaining == 0):
            raise ValueError('Additional observation is unavailable')
        number = self.count
        self.count += 1
        return number


def apply_action(state, action):
    """调用者先用原型parse校验；这里再次限制实际可执行的两项调整。"""
    from copy import deepcopy
    result = deepcopy(state)
    name, args = action['id'], action['args']
    if name == 'SET_TIME_SCALE':
        result['parameters']['time_scale'] = args['value']
    elif name == 'SET_GRASP_OFFSET':
        old = result['parameters']['grasp_offset']
        result['parameters']['grasp_offset'] = [a+b for a, b in zip(old, args['delta_m'])]
    elif name != 'RETRY':
        raise ValueError('Not an executable action in this bridge')
    from loopstudy.actions import validate
    return validate(result)
