from rv_runtime import VerticalSession
from self_geometry import context
from contact_capture import capture


class SelfSession(VerticalSession):
    def _engine(self):
        with context(), capture(self.folder/'contacts.jsonl', self.case['item']):
            super()._engine()
