from pathlib import Path
from types import SimpleNamespace
from nc_state import Branch
from live_telemetry import Recorder
from sv_common import ROOT, read, save, sha
from sv_requests import build
from sv_actions import check


def public(value):
    forbidden = {'root_cause', 'error_type', 'grasp_residual_xy', 'contact_details', 'source_center',
        'source_half', 'bin_center', 'qualification', 'successor', 'verified_recovery', 'selected_candidate_index'}
    if isinstance(value, dict):
        assert not forbidden.intersection(value)
        for child in value.values():
            public(child)
    elif isinstance(value, list):
        for child in value:
            public(child)


def run(target):
    source = ROOT.parent/'natural_qualified_pilot_v1'
    name = 'C0_962703_varied_noisy'
    audit = read(source/'audits'/(name+'.json'))
    assert audit['passed'] and audit['manifest_sha256'] == sha(source/'manifest.json')
    folder = source/'cases'/name/'attempt_1'
    case = next(c for c in read(source/'manifest.json')['cases'] if c['item']['id'] == name)
    for path in folder.rglob('*'):
        if path.is_file():
            assert sha(path) == audit['identities'][str(path)]
    step, summary = read(folder/'step.json'), read(folder/'observation_summary.json')
    recorder = Recorder()
    recorder.rows = read(folder/'telemetry.json')['rows']
    session = SimpleNamespace(folder=folder, step=step, recorder=recorder, record=read(step['result_path'])['records'][0])
    observed = SimpleNamespace(paths=summary['paths'],
        sampler=SimpleNamespace(rows=summary['public'], private=summary['private']))
    bundle = build(Branch(case['item'], step), session, observed)
    public(bundle['request'])
    assert bundle['direct_messages'][1] == bundle['diagnostic_messages'][1]
    assert all(sha(p) == h for p,h in zip(bundle['visual']['paths'], bundle['visual']['sha256']))
    check(dict(id='SET_GRASP_OFFSET', args=dict(delta_m=[0., 0., -.03])), bundle['request'])
    save(target/'input_check.json', dict(passed=True, source=name, model_calls=0, physical_attempts=0))
    save(target/'input_example.json', bundle)
