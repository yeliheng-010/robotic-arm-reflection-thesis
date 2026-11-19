import json
import numpy as np
from surface_grasp_v1.common import read,sha

PHASES=('after_lift','before_release')


def compare_search(one,two):
    ignored='framing'
    rows=[]
    for a,b in zip(one['attempts'],two['attempts']):
        x={k:v for k,v in a['report'].items() if k!=ignored}
        y={k:v for k,v in b['report'].items() if k!=ignored}
        rows.append(dict(index=a['index'],camera_equal=a['camera']==b['camera'],
            measurement_and_decision_equal=x==y,
            framing_exact=a['report'].get(ignored)==b['report'].get(ignored)))
    equal=(len(one['attempts'])==len(two['attempts']) and
           all(r['camera_equal'] and r['measurement_and_decision_equal'] for r in rows))
    return dict(strict_equal=one==two,measurement_and_decision_equal=equal,rows=rows)


def compare_saved(folder,output):
    original,current=read(folder/'result.json'),read(output/'result.json')
    assert original['views']==current['views']==0,'Diagnostic scope is zero accepted views only'
    first,second=read(folder/'snapshot.json'),read(output/'snapshot.json')
    assert sha(folder/'state.npz')==first['state_sha256']
    assert sha(output/'state.npz')==second['state_sha256']
    assert first==second
    with np.load(folder/'state.npz') as a,np.load(output/'state.npz') as b:
        np.testing.assert_array_equal(a['state'],b['state'])
    search=compare_search(read(folder/'camera_search.json'),read(output/'camera_search.json'))
    return dict(integration_state_identical=True,result_equal=original==current,search=search,
                strict_replay_passed=original==current and search['strict_equal'])


def summarize_search(folder):
    data=read(folder/'camera_search.json')
    reports=[x['report'] for x in data['attempts']]
    gates=[r['gate'] for r in reports if 'gate' in r]
    counts={}
    for gate in gates:
        for name in gate['rejected']:
            counts[name]=counts.get(name,0)+1
    fractions=[g['objects']['PurpleCapsule']['visible_fraction'] for g in gates]
    return dict(checked=data['checked'],accepted=len(data['accepted']),rejected_objects=counts,
        framing_rejected=sum(r.get('reason')=='framing_rejected' for r in reports),
        source_visible_fraction_original=reports[0]['gate']['objects']['PurpleCapsule']['visible_fraction'],
        source_visible_fraction_max=max(fractions),quality_passed=read(folder/'result.json')['quality_passed'])


def contact_rows(folder):
    return [json.loads(s) for s in (folder/'contacts.jsonl').read_text().splitlines()]


def trace(current,old):
    a=contact_rows(current)
    b=[r for r in contact_rows(old) if r['action'] in ('move_to_grasp_pose','close_gripper','move_to_point')]
    assert len(a)==len(b)
    differences=[dict(index=i,event=x['event'],time=x['time'],
        fields=[k for k in sorted(set(x)|set(y)) if x.get(k)!=y.get(k)])
        for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    plans=read(current/'bridge.json')['planners']
    same_commands=plans==read(old/'bridge.json')['planners'][:len(plans)]
    core=('qpos','ctrl','command','closure','time','step','action','event','pads')
    core_equal=all(all(x[k]==y[k] for k in core) for x,y in zip(a,b))
    return dict(rows=len(a),exactly_equal_rows=len(a)-len(differences),differences=differences,
        full_trace_identical=a==b,recorded_command_joint_control_equal=core_equal,
        commands_equal=same_commands,last_source_distance_m=float(np.linalg.norm(
            np.asarray(a[-1]['source'])-b[-1]['source'])))
