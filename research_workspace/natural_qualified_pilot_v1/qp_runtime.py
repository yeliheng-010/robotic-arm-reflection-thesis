from rv_runtime import VerticalSession
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from contact_capture import capture


class QualifiedSession(VerticalSession):
    def _engine(self):
        with self_context(),joint_context(self.case['config']),capture(self.folder/'contacts.jsonl',self.case['item']):
            super()._engine()
