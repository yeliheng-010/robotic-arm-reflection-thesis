from pathlib import Path
from nc_audit_attempt import audit
from rb_audit import route
from cp_audit import candidate_audit
from rv_runtime import mode
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from sr_audit import measured
from sv_common import read


def inspect(case, step):
    assert step['control'] == case['control'] == dict(grasp_mode='world_down')
    with self_context(), joint_context(case['config']), mode(case['control']):
        record, recorder, groups = audit(case, step)
        geometry = route(case, step, record)
    candidate_audit(step, case['config'])
    contact = measured(Path(step['session_path']))
    return dict(record=record, recorder=recorder, geometry=geometry,
        contact={k:v for k,v in contact.items() if k != 'closing_end'})
