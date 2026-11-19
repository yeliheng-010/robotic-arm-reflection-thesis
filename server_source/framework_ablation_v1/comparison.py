"""同状态反馈/候选配对和预算延长的严格前缀核验。"""
import importlib.util
from common import ROOT,PARENT,read


def helper(folder,name):
    spec=importlib.util.spec_from_file_location(folder+'_'+name,PARENT/folder/f'{name}.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def matched_inputs(pairs):
    known,counts={},dict(feedback=0,candidates=0)
    for entry,result in pairs:
        for index,decision in enumerate(result['decisions']):
            key=(entry['item']['scene_id'],decision['after_attempt'])
            step=result['attempts'][index]
            for prior_entry,prior,prior_step in known.get(key,[]):
                if prior['before']!=decision['before']:
                    continue
                assert prior['feedback']==decision['feedback']
                assert prior_step['projection_seed']==step['projection_seed']
                assert prior_step['noise_audit']==step['noise_audit']
                counts['feedback']+=1
                if 'retry' not in (entry['method'],prior_entry['method']):
                    assert prior['candidates']==decision['candidates']
                    counts['candidates']+=1
            known.setdefault(key,[]).append((entry,decision,step))
    return counts


def budget_prefixes(pairs):
    checks=dict(tasks=0,attempts=0,decisions=0)
    for entry,later in pairs:
        if entry['max_attempts']!=4:
            continue
        prior=read(ROOT/'tasks'/entry['uid'].replace('b4__','b3__',1)/'result.json')
        assert len(later['attempts'])>=len(prior['attempts'])
        for left,right in zip(prior['attempts'],later['attempts']):
            ignored={'result_path','result_sha256'}
            assert {k:v for k,v in left.items() if k not in ignored}=={
                k:v for k,v in right.items() if k not in ignored},entry['uid']
            checks['attempts']+=1
        for left,right in zip(prior['decisions'],later['decisions']):
            assert {k:v for k,v in left.items() if k!='event'}=={k:v for k,v in right.items() if k!='event'}
            if 'event' in left:
                for field in ('request','text'):
                    assert left['event'][field]==right['event'][field]
            checks['decisions']+=1
        assert len(later['decisions'])>=len(prior['decisions'])
        checks['tasks']+=1
    return checks


def paired_physics(pairs):
    values=[v for _,v in pairs]
    return dict(paired_initials=helper('route_loop_v1','verify').paired_initials(values),
                **helper('route_loop_v1','compare').compare_physics(values),
                matched_inputs=matched_inputs(pairs))
