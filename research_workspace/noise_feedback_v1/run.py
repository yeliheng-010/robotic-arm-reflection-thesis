"""冻结4条真实来源，检查72个投影的可追溯性与候选合法性。"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from collections import Counter
import numpy as np
from projection import project,profiles,FIELDS,CLIP
from semanticfix2.context import enrich,project as clean_project
from semanticfix2.protocol import sha
from loopstudy.actions import candidates,validate
from loopstudy.protocol import verify as loop_verify
from stability.collection_status import atomic

ROOT=Path('/home/yeliheng/grasp_server/noise_feedback_v1')
BASE=ROOT.parent
SEEDS=(907001,907002,907003)


def fixtures():
    rows=[]
    directory=BASE/'route_loop_v1/tasks/Q1_905001_position_only_new_rule'
    task=json.loads((directory/'result.json').read_text())
    for step in task['attempts'][:2]:
        rows.append(dict(id=f"collision_{step['index']}",report=step['feedback'],state=step['state'],
            path=step['result_path'],sha256=step['result_sha256']))
    path=BASE/'recovery_study_v1/tasks/F_ideal_priority/result.json'
    old=json.loads(path.read_text())
    for index,record in enumerate(old['records'][:2]):
        assert record['error']
        shown=clean_project(enrich(record['error'],attempt=index+1),old['scenario'],attempt=index+1)
        rows.append(dict(id=f'residual_{index+1}',report=shown,
            state=dict(parameters=record['parameters'],profile='original'),path=str(path),sha256=sha(path)))
    return rows


def manifest():
    loop_verify()
    return dict(fixtures=fixtures(),profiles=profiles(),seeds=SEEDS,
        source_protocol_sha256=sha(BASE/'route_loop_v1/protocol.json'),
        code={p.name:sha(p) for p in sorted(ROOT.glob('*.py'))},expected=72,model_calls=0,physical_runs=0)


def check_one(fixture,profile,seed):
    raw=deepcopy(fixture['report'])
    shown,trace=project(raw,profile,seed=seed)
    assert raw==fixture['report'] and (shown,trace)==project(raw,profile,seed=seed)
    rows=candidates(shown,fixture['state'],[])
    for row in rows:
        validate(row['state'])
    for field,entry in trace.items():
        assert max(abs(d) for d in entry['delta'])<=CLIP*profile['sigma_m']
        if entry['missing']:
            assert field not in shown['evidence']
            kind='measured_grasp' if field==FIELDS[0] else 'measured_place'
            assert all(r['kind']!=kind for r in rows)
        else:
            np.testing.assert_allclose(np.array(entry['original'])+entry['delta'],shown['evidence'][field],atol=0,rtol=0)
    for field,value in raw['evidence'].items():
        if field not in FIELDS and field!='measurement_protocol':
            assert shown['evidence'][field]==value
    return dict(fixture=fixture['id'],profile=profile,seed=seed,shown=shown,audit=trace,candidates=rows)


def run():
    saved=json.loads((ROOT/'protocol.json').read_text())
    assert saved==json.loads(json.dumps(manifest()))
    rows=[check_one(f,p,s) for f in saved['fixtures'] for p in saved['profiles'] for s in saved['seeds']]
    assert len(rows)==72 and not (ROOT/'result.json').exists()
    summary=dict(passed=True,projections=len(rows),fixtures=len(saved['fixtures']),model_calls=0,physical_runs=0,
        missing_fields=sum(e['missing'] for r in rows for e in r['audit'].values()),
        error_types=dict(Counter(f['report']['error_type'] for f in saved['fixtures'])),training_approved=0)
    assert saved==json.loads(json.dumps(manifest()))
    atomic(ROOT/'result.json',dict(summary=summary,rows=rows))
    atomic(ROOT/'verification.json',summary)
    print(json.dumps(summary))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--freeze',action='store_true')
    if parser.parse_args().freeze:
        with (ROOT/'protocol.json').open('x') as stream:
            json.dump(manifest(),stream,ensure_ascii=False,indent=2)
    else:
        run()
