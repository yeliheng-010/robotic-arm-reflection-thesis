"""机制是否实际出现，与技术审计是否通过分别记录。"""
import numpy as np
from pilot import read
from sensor import relevant


def route_side_effect(trace):
    found=[]
    for i,d in enumerate(trace['decisions']):
        if not d['selected'] or d['selected']['kind']!='descent_route':
            continue
        if i+1>=len(trace['attempts']):
            continue
        later=trace['attempts'][i+1]
        error=(later['feedback'] or {}).get('error_type')
        if error not in ('object_outside_container','placement_offset'):
            continue
        follow=trace['attempts'][i+2:] if i+2<len(trace['attempts']) else []
        recollision=any((s['feedback'] or {}).get('error_type')=='collision' for s in follow)
        found.append(dict(route=d['selected']['state']['profile'],placement_failure_after_route=True,
                          later_collision=recollision,after_attempt=i+2))
    return found


def exposure(value):
    traces={p.split('/')[-2]:read(p) for p in value['trajectories']}
    output=dict(related_missing=0,related_outlier=0,reacquired=0,side_effects=[],comparison=[])
    seen=set()
    for name,t in traces.items():
        output['side_effects'].extend(dict(mode=name,**r) for r in route_side_effect(t))
        for d in t['decisions']:
            o=d['observation']
            field=o['target_field']
            if not field:
                continue
            for s in o['samples']:
                key=(s['source_sha256'],s['number'],field)
                if key not in seen and field in s['audit']:
                    a=s['audit'][field]
                    output['related_missing']+=a['missing']
                    output['related_outlier']+=a['outlier']
                    seen.add(key)
            first=o['samples'][0]
            if field not in first['feedback']['evidence'] and field in o['feedback']['evidence']:
                output['reacquired']+=1
    if 'latest' in traces and 'median' in traces and traces['latest']['decisions'] and traces['median']['decisions']:
        a,b=(traces[m]['decisions'][0]['observation'] for m in ('latest','median'))
        assert a['samples']==b['samples'],'Initial observation budget/input mismatch'
        field=a['target_field']
        if field and field in a['samples'][0]['audit']:
            truth=np.asarray(a['samples'][0]['audit'][field]['original'])
            output['comparison'].append(dict(field=field,same_snapshot=True,
                latest_error_m=float(np.linalg.norm(np.asarray(a['feedback']['evidence'][field])-truth)),
                median_error_m=float(np.linalg.norm(np.asarray(b['feedback']['evidence'][field])-truth))))
    mechanism=value['scene']['mechanism']
    output['mechanism_exposed']=(output['related_missing']>0 if mechanism=='occlusion' else
        output['related_outlier']>0 if mechanism=='outlier' else bool(output['side_effects']))
    output['observed_success_path']=any(t['success'] for t in traces.values())
    output['trace_lengths']={name:len(t['attempts']) for name,t in traces.items()}
    return output
