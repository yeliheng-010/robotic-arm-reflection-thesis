"""冻结旧混合方法；新增显式阶段基线与诊断序列。"""
from reflection.reflector import Reflection
from flashnext.client import generate,append,parse_correction
from controlled.config import MAX_TOKENS
from controlled.feedback import check_action
from nextstudy.prompt import messages
from bounded.candidates import candidates
from bounded.baselines import CandidateBaseline,priority
from bounded.client import HybridSelector
from recovery.design import sequence_changes,SELECTION_SEED


def choose_stage(rows,parameters,*,report):
    phase = report.get('evidence',{}).get('diagnostics',{}).get('motion_segment')
    lifting = [r for r in rows if r['kind']=='exploratory_lift']
    if report['error_type']=='collision' and phase in ('transport','lift') and lifting:
        return min(lifting,key=lambda r:r['id'])
    return min(rows,key=lambda r:priority(r,parameters))


class StageRule:
    def __init__(self,directory):
        self.path = directory/'baseline_choices.jsonl'

    def reflect(self,report,parameters,history=()):
        rows = candidates(report.to_dict(),parameters.to_dict(),history)
        if not rows:
            raise RuntimeError('Candidate set exhausted')
        selected = choose_stage(rows,parameters,report=report.to_dict())
        answer = Reflection(selected['explanation'],selected['changes'],'rule_candidates_stage')
        append(self.path,dict(candidates=rows,selected=selected['id'],answer=answer.to_dict(),model=None))
        return answer


class SequenceRule:
    def __init__(self,directory,*,mode):
        self.path,self.mode = directory/'sequence.jsonl',mode

    def reflect(self,report,parameters,history=()):
        changes = sequence_changes(self.mode,parameters,step=len(history))
        answer = Reflection('预登记诊断动作，效果待验证：'+str(changes),changes,'diagnostic_rule_sequence')
        check_action(answer,parameters,candidate_count=report.evidence['diagnostics'].get('available_candidate_count'))
        append(self.path,dict(mode=self.mode,step=len(history),answer=answer.to_dict(),model=None))
        return answer


class GuidedFlash:
    def __init__(self,instruction,directory):
        self.instruction,self.path = instruction,directory/'requests.jsonl'

    def reflect(self,report,parameters,history=()):
        prompt = messages(self.instruction,report.to_dict(),parameters=parameters.to_dict(),history=history,variant='guided')
        event = generate(prompt,max_tokens=MAX_TOKENS)
        try:
            if 'error' in event:
                raise ValueError(event['error'])
            count = report.evidence.get('diagnostics',{}).get('available_candidate_count')
            answer = parse_correction(event['text'],parameters,candidate_count=count)
            check_action(answer,parameters,candidate_count=count)
            event['parsed'] = answer.to_dict()
            return answer
        except (ValueError,KeyError,TypeError) as error:
            event['error'] = repr(error)
            raise RuntimeError('Guided generation failed: '+str(error)) from error
        finally:
            append(self.path,event)


def make(item,directory,*,instruction):
    arm = item['arm']
    if arm=='retry':
        return None
    if arm=='hybrid':
        return HybridSelector(directory)
    if arm=='guided':
        return GuidedFlash(instruction,directory)
    if arm=='rule_stage':
        return StageRule(directory)
    if arm in ('priority','random'):
        return CandidateBaseline(directory,mode=arm,seed=SELECTION_SEED+item['seed'])
    return SequenceRule(directory,mode=arm)
