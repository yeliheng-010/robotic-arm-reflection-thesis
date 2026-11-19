"""仅改变反思器可见反馈；物理记录独立保留。"""
import copy
from controlled.feedback import project_report,check_action,RESIDUALS
from reflection.errors import ErrorReport,ErrorType
from flashnext.client import append


def project(report,config,*,attempt):
    value = project_report(report,config,attempt=attempt)
    if config['feedback'].get('hide_xy'):
        for field in RESIDUALS:
            value['evidence'].pop(field,None)
    return value


class FeedbackAdapter:
    def __init__(self,inner,config,*,directory):
        self.inner,self.config = inner,config
        self.path,self.history,self.calls = directory/'feedback.jsonl',[],0

    def reflect(self,report,parameters,history=()):
        self.calls += 1
        projected = project(report.to_dict(),self.config,attempt=self.calls)
        event = dict(attempt=self.calls,projected=projected,history=copy.deepcopy(self.history))
        value = ErrorReport(ErrorType(projected['error_type']),projected['message'],
                            projected['evidence'],detector=projected['detector'],timestamp=0)
        try:
            answer = self.inner.reflect(value,parameters,self.history)
            count = value.evidence['diagnostics'].get('available_candidate_count')
            check_action(answer,parameters,candidate_count=count)
            event['answer'] = answer.to_dict()
            self.history.append({'error':projected,'reflection':answer.to_dict()})
            return answer
        except (ValueError,RuntimeError) as error:
            event['error'] = repr(error)
            raise
        finally:
            append(self.path,event)
