"""记录实际错误类型，区分干预标签与观察到的失败。"""
import json
from collections import Counter
from pathlib import Path
from hardstudy.design import ROOT


def counts(protocol,results):
    observed=Counter()
    for item in protocol['scenes']:
        path=ROOT/'qualification'/item['id']/'result.json'
        if not (path.parent/'summary.json').exists():
            continue
        value=json.loads(path.read_text())
        if len(value['steps'])==2:
            step=value['steps'][1]
            feedback=step['feedback'] or {}
            observed[(item['factor'],feedback.get('error_type','success'))]+=1
    terminal,invalid=Counter(),Counter()
    for result in results:
        feedback=result['attempts'][-1]['feedback'] or {}
        terminal[(result['item']['factor'],result['item']['arm'],feedback.get('error_type','success'))]+=1
        for decision in result['decisions']:
            if decision['selected'] is not None:
                continue
            kind='candidate_exhausted' if not decision['candidates'] else 'model_invalid'
            if decision.get('event',{}).get('service_error'):
                kind='service_error'
            invalid[(result['item']['arm'],kind)]+=1
    return dict(qualification_outcomes=[dict(factor=k[0],outcome=k[1],n=n) for k,n in sorted(observed.items())],
                terminal_outcomes=[dict(factor=k[0],arm=k[1],outcome=k[2],n=n) for k,n in sorted(terminal.items())],
                invalid_breakdown=[dict(arm=k[0],reason=k[1],n=n) for k,n in sorted(invalid.items())])
