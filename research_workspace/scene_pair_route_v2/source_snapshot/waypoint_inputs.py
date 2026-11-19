from pathlib import Path
from sd_common import read, sha
from route_prepare import verify as verify_previous
from waypoint_policy import allowed

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent/'scene_pair_route_v1'


def inputs():
    manifest = verify_previous()
    assert read(PREVIOUS/'verification.json')['passed']
    result = []
    for case in manifest['cases']:
        if case['reused_success']:
            result.append(dict(case, steps=[case['first']]))
            continue
        folder = PREVIOUS/'physics'/case['id']
        previous = read(folder/'result.json')
        assert len(previous['steps']) == 2 and previous['steps'][0] == case['first']
        last = previous['steps'][-1]
        assert sha(last['result_path']) == last['result_sha256']
        trace_path = folder/'attempt_2/route.json'
        trace = read(trace_path)
        record = read(last['result_path'])['records'][0]
        assert allowed(record, trace, case['item']['destination'])
        result.append(dict(case, steps=previous['steps'], prior_trace=str(trace_path)))
    return result
