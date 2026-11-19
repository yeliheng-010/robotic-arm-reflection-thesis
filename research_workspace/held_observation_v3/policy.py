from surface_grasp_v1.common import read,sha


def assess(observation,replay):
    ready=(observation['views']>=1 and observation['state_unchanged']
           and not observation['release_authorized'] and replay['independently_identical'])
    return dict(capture_ready=bool(ready),control_ready=False,
                pose_quality_passed=observation['quality_passed'],release_authorized=False)


def metadata(folder):
    value=read(folder/'calibration.json')
    assert sha(folder/'rgb.png')==value['rgb_sha256'],'RGB integrity mismatch'
    assert sha(folder/'sensor.npz')==value['sensor_sha256'],'Sensor integrity mismatch'
    return {key:entry for key,entry in value.items() if key!='rgb_sha256'}
