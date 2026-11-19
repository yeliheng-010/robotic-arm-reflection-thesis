"""安全原方案优先及全局检查预算。"""


class Budget:
    def __init__(self, maximum):
        self.maximum,self.used = maximum,0


def select(original, alternatives, *, check, budget, record):
    return None


def staged(primary, fallback):
    return primary()
