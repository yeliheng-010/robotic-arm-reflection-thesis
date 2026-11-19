"""候选集合相同的规则/随机选择基线，量化模型选择的增益。"""
import random
from pathlib import Path
from reflection.reflector import Reflection
from flashnext.client import append
from bounded.candidates import candidates


def priority(row, parameters):
    kind = row['kind']
    if kind.startswith('measured_'):
        return (0,row['id'])
    field = next(iter(row['changes']))
    if kind=='exploratory_depth' and row['changes'][field][2] < parameters.grasp_offset[2]:
        return (1 if parameters.candidate_index>0 else 3,row['id'])
    if kind=='exploratory_candidate' and row['changes'][field]==parameters.candidate_index+1:
        return (2,row['id'])
    return (4,row['id'])


class CandidateBaseline:
    def __init__(self,directory,*,mode,seed):
        self.path = Path(directory)/'baseline_choices.jsonl'
        self.mode,self.rng = mode,random.Random(seed)

    def reflect(self,report,parameters,history=()):
        rows = candidates(report.to_dict(),parameters.to_dict(),history)
        if not rows:
            raise RuntimeError('Candidate set exhausted')
        selected = self.rng.choice(rows) if self.mode=='random' else min(rows,key=lambda r:priority(r,parameters))
        answer = Reflection(selected['explanation'],selected['changes'],'rule_candidates_'+self.mode)
        append(self.path,dict(candidates=rows,selected=selected['id'],answer=answer.to_dict(),model=None))
        return answer
