"""独立检查观测顶面目标来源、接触、路径以及相同配对条件。"""
import sys
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import rb_audit
import geometry_v3
import sv_strategy_audit
from audit_v5 import audit_attempt
from iv3_geometry import strict_compare, ReconstructionMismatch
from nc_audit_frames import frame
from sr_audit import measured
from cc_audit import visibility
from ta_common import PILOT, current, read, save, sha
from ta_protocol import validate_pair


def observations(case, folder):
    initial = visibility(folder/'initial_visibility.json', case['config'])
    assert initial['accepted']
    final = visibility(folder/'observations/visibility_0.json', case['config'])
    summary = read(folder/'observation_summary.json')
    expected = folder/('observations' if final['accepted'] else 'private_audit')/'observation_0'
    assert summary['paths'] == [str(expected)]
    public, private = frame(expected, case['config'], attempt=1, index=0)
    assert summary['public'] == [public] and summary['private'] == [private]
    assert read(folder/'publication.json')['public_input_allowed'] == final['accepted']
    return dict(initial=initial, final=final)


def inspect(case, reference):
    validate_pair(reference['case'], case)
    folder = PILOT/'cases'/str(case['item']['seed'])
    result, step = read(folder/'result.json'), read(folder/'first/step.json')
    old = read(reference['step'])
    assert result['physical_attempts'] == step['index'] == old['index'] == 1
    assert result['manifest_sha256'] == sha(PILOT/'manifest.json')
    assert old['state'] == step['state'] and old['control'] == step['control']
    assert old['strategy'] == 'original' and step['strategy'] == 'observed_top'
    seen = observations(case, folder/'first')
    assert result['public_input_allowed'] == seen['final']['accepted']
    contact = measured(folder/'first')
    if contact['self_contact_samples']:
        return dict(passed=False, reason='measured_robot_self_contact')
    with patch.object(geometry_v3, 'compare', strict_compare), \
         patch.object(rb_audit, 'geometry', geometry_v3.audit), \
         patch.object(sv_strategy_audit, 'audit_attempt', audit_attempt):
        try:
            evidence = sv_strategy_audit.inspect(case, step)
        except ReconstructionMismatch as error:
            return dict(passed=False, reason='dynamic_geometry_reconstruction_mismatch', evidence=error.evidence)
    assert step['success'] == result['new_success']
    return dict(passed=True, old_success=old['success'], new_success=result['new_success'],
        observations=seen, geometry=evidence['geometry'], contact=evidence['contact'])


if __name__ == '__main__':
    case, reference = current(int(sys.argv[1]))
    result = inspect(case, reference)
    files = [p for p in (PILOT/'cases'/str(case['item']['seed'])).rglob('*') if p.is_file()]
    result.update(identities={str(p): sha(p) for p in files}, manifest_sha256=sha(PILOT/'manifest.json'))
    save(PILOT/'audits'/(str(case['item']['seed'])+'.json'), result)
    print(dict(seed=case['item']['seed'], passed=result['passed']), flush=True)
