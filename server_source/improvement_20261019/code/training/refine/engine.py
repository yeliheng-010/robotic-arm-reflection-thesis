"""只增加可观测证据的实验引擎；物理执行仍调用冻结原实现。"""
import json

from reflection.engine import FeedbackEngine
from training.refine.instrumentation import capture, diagnostic_snapshot


class EvidenceEngine(FeedbackEngine):
    def _attempt(self, *args, **kwargs):
        state = {}
        with capture(state):
            record, report = super()._attempt(*args, **kwargs)
        evidence = diagnostic_snapshot(state, report)
        if report is not None:
            report.evidence['diagnostics'] = evidence
            record['error'] = report.to_dict()
        record['diagnostics'] = evidence
        directory = kwargs.get('directory') if 'directory' in kwargs else args[6]
        (directory / 'diagnostics.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
        return record, report

