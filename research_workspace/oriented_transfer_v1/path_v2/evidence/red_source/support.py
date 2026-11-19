"""RED：仍然仅允许初始一帧支撑。"""
class Guard:
    def __init__(self, baseline):
        self.first=True

    def check(self, contacts, *, rising):
        accepted=self.first and rising
        self.first=False
        return [] if accepted else contacts
