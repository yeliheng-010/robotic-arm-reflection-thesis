"""合成语义用例；期待答案不会进入模型请求。"""
from reflection.reflector import Parameters
from reflection.errors import ErrorReport, ErrorType


def measured(identifier, group, *, target, current, residual):
    grasp = target == 'grasp_offset'
    kind = ErrorType.EMPTY_GRASP if grasp else ErrorType.OBJECT_OUTSIDE_CONTAINER
    key = 'grasp_residual_xy' if grasp else 'placement_residual_xy'
    evidence = {key: residual, 'diagnostics': {
        'failure_stage': 'grasp' if grasp else 'placement',
        'available_candidate_count': 3, 'selected_candidate_index': 0},
        'measurement_protocol': {'mode':'ideal_measurement', 'units':'metres'}}
    report = ErrorReport(kind, 'Detected task failure: '+kind.value, evidence,
                         detector='synthetic_semantic_fixture', timestamp=0).to_dict()
    expected = [max(-.25, min(.25, current[i]-residual[i])) for i in range(2)]+[current[2]]
    return dict(id=identifier, group=group, report=report,
                parameters=Parameters().updated({target:current}).to_dict(),
                target=target, expected=expected, history=[], forbidden=[])


def fixtures():
    rows = []
    for target, short in (('grasp_offset','grasp'), ('place_offset','place')):
        for sign, label in ((1,'positive'), (-1,'negative')):
            rows.append(measured(f'sign_{short}_{label}', 'sign', target=target,
                                 current=[0,0,0], residual=[sign*.04,-sign*.02]))
            rows.append(measured(f'absolute_{short}_{label}', 'absolute', target=target,
                                 current=[sign*.06,-sign*.02,0], residual=[sign*.02,-sign*.03]))
            rows.append(measured(f'bound_{short}_{label}', 'bound', target=target,
                                 current=[0,0,0], residual=[sign*.31,0]))
    for identifier, kind, stage, residual, forbidden in (
        ('missing_place', ErrorType.OBJECT_OUTSIDE_CONTAINER, 'placement', {}, []),
        ('missing_grasp', ErrorType.EMPTY_GRASP, 'grasp', {}, []),
        ('stage_pregrasp', ErrorType.IK_FAILURE, 'pregrasp',
         {'placement_residual_xy':[.04,0]}, ['place_offset','lift_height']),
        ('stage_transport', ErrorType.OBJECT_DROPPED, 'transport', {}, ['place_offset'])):
        evidence = dict(residual, diagnostics=dict(failure_stage=stage,
                        available_candidate_count=3, selected_candidate_index=0),
                        measurement_protocol=dict(mode='simulated_measurement', units='metres'))
        report = ErrorReport(kind, 'Detected task failure: '+kind.value, evidence,
                             detector='synthetic_semantic_fixture', timestamp=0).to_dict()
        rows.append(dict(id=identifier, group='missing_or_stage', report=report,
                         parameters=Parameters().to_dict(), target=None, expected=None,
                         history=[], forbidden=forbidden))
    return rows
