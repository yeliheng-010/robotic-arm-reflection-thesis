"""审计全部源失败、固定请求和动作全集后冻结。"""
from pathlib import Path
import unittest
from rc_common import verify as source_verify
from rc_audit import audit_scene
from rc_policy import messages, visible_history
from loopstudy.actions import candidates, validate, choose_rule
from cd_common import ROOT, SOURCE, LAYOUT, read, save, sha
from cd_design import request, branches, smoke_indices


def make_case(source):
    folder = SOURCE/'tasks'/source['item']['id']
    model, rule = (read(folder/method/'result.json') for method in ('model','rule'))
    assert len(model['attempts']) == len(rule['attempts']) == 3
    step, decision = model['attempts'][1], model['decisions'][1]
    assert not step['success'] and step['state'] == rule['attempts'][1]['state']
    assert step['feedback'] == rule['attempts'][1]['feedback']
    assert model['decisions'][0]['selected'] == rule['decisions'][0]['selected']
    options = candidates(step['feedback'],step['state'],model['decisions'][:1],legacy=False)
    assert options == decision['candidates'] == rule['decisions'][1]['candidates']
    expected = messages(step,options,visible_history(model['attempts'][:2],model['decisions'][:1]))
    assert expected == decision['event']['request']['messages']
    assert choose_rule(options,step['state'],report=step['feedback']) == rule['decisions'][1]['selected']
    return dict(id=source['item']['id'],source=source,snapshot=step,candidates=options,
        request=decision['event']['request'],original_text=decision['event']['text'],
        model_action=decision['selected'],rule_action=rule['decisions'][1]['selected'],
        model_final=model['attempts'][2],rule_final=rule['attempts'][2])


def frozen_files(cases):
    files = set(ROOT.glob('*.py')) | set(ROOT.glob('*.sh')) | set(ROOT.glob('*.sbatch'))
    files.add(ROOT/'PROTOCOL.md')
    files.update(SOURCE/name for name in ('manifest.json','verification.json'))
    files.update(LAYOUT/name for name in ('manifest.json','plan.json','verification.json'))
    for case in cases:
        files.update((SOURCE/'tasks'/case['id']).rglob('*.json'))
    return files


def source_cases():
    source = source_verify()
    final = read(SOURCE/'verification.json')
    assert final['passed'] and final['complete'] and final['accounted'] == 160
    selected = [r for r in source['rows'] if not r['success']]
    assert len(selected) == 11
    for row in selected:
        audit_scene(row['index'],source)
    return source, [make_case(r) for r in selected]


def freeze():
    assert not (ROOT/'manifest.json').exists()
    from check_structure import main as check_structure
    check_structure()
    source, cases = source_cases()
    rows = branches(cases)
    assert len(rows) == 73 and sum(r['origin']=='original_menu' for r in rows) == 67
    for row in rows:
        validate(row['action']['state'])
    suite = unittest.defaultTestLoader.discover(str(ROOT),pattern='test_design.py')
    tests = unittest.TextTestRunner(verbosity=2).run(suite)
    assert tests.wasSuccessful() and tests.testsRun == 8
    identities = dict(source['identities'])
    identities.update({str(p):sha(p) for p in frozen_files(cases)})
    manifest = dict(cases=cases,branches=rows,smoke=smoke_indices(rows,cases),identities=identities,
        test_used=False,training_approved=False,task_model_calls=44,new_physical=73)
    save(ROOT/'manifest.json',manifest)
    save(ROOT/'preflight.json',dict(passed=True,cases=11,branches=73,tests=tests.testsRun,
        task_model_calls=44,smoke=manifest['smoke'],manifest_sha256=sha(ROOT/'manifest.json')))
    print('PASS: 11 cases, 44 task calls, 73 physical branches',flush=True)


if __name__ == '__main__':
    freeze()
