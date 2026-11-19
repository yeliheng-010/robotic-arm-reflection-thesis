"""复核实际参数、初态、同参数物理结果与接触AABB计算。"""
import json
import numpy as np
from recovery.references import BASE
from semanticfix2.design import configuration
from semanticfix2.context import stage_context

TOLERANCE = 1e-8


def audit_contacts(report):
    if not report or report['error_type']!='collision':
        return 0
    evidence = report['evidence']
    details = evidence['contact_details']
    assert details['attempt']==1 and details['contacts']
    assert details['motion_context']['phase']==stage_context(evidence['diagnostics'])['phase']
    wanted = {frozenset(p) for p in evidence['contacts']}
    for contact in details['contacts']:
        assert frozenset(g['root'] for g in contact['geometries']) in wanted
        for geom in contact['geometries']:
            raw = geom['native']
            box = np.array(raw['local_aabb'])
            rotation = np.array(raw['xmat']).reshape(3,3)
            center = np.array(raw['xpos'])+rotation@box[:3]
            extent = np.abs(rotation)@box[3:]
            np.testing.assert_allclose(center-extent,geom['aabb']['low'],atol=TOLERANCE,rtol=0)
            np.testing.assert_allclose(center+extent,geom['aabb']['high'],atol=TOLERANCE,rtol=0)
    return len(details['contacts'])


def audit(result,item):
    assert result['scenario']==configuration(item) and result['item']==item
    assert result['attempts']==len(result['records'])==1
    assert result['test_used'] is False and result['training_approved'] is False
    record = result['records'][0]
    assert record['parameters']==item['parameters']
    assert result['success']==record['accepted']
    assert not record['accepted'] or record['physical_success']
    assert not result['llm_stats'] and 'reflection' not in record
    root = BASE/'recovery_study_v1/tasks'
    original = json.loads((root/f"{item['scene_id']}_retry/result.json").read_text())['records'][0]
    for field in ('initial_qpos','initial_body_xyz'):
        np.testing.assert_allclose(original['candidate_trace'][field],record['candidate_trace'][field],atol=TOLERANCE,rtol=0)
    matched = item['variant'] in ('default','lift45')
    if item['variant']=='lift45':
        original = json.loads((root/f"{item['scene_id']}_rule_stage/result.json").read_text())['records'][1]
    if matched:
        assert record['parameters']==original['parameters']
        assert record['accepted']==original['accepted']
        assert record['error']['error_type']==original['error']['error_type']
        assert record['diagnostics']['motion_segment']==original['diagnostics']['motion_segment']
        np.testing.assert_allclose(record['evaluation']['position'],original['evaluation']['position'],atol=TOLERANCE,rtol=0)
    assert record['diagnostics']['selected_candidate_index']==record['parameters']['candidate_index']
    contacts = audit_contacts(record.get('error'))
    return dict(passed=True,initial_paired=True,parameters_verified=True,
                unchanged_physics_at_same_parameters=matched,contact_records=contacts)
