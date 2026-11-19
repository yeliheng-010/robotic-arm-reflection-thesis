import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from held_observation_v3.policy import assess, metadata


class PolicyTests(unittest.TestCase):
    def test_one_qualified_view_allows_diagnosis_not_control(self):
        observed=dict(views=1,state_unchanged=True,quality_passed=False,
                      release_authorized=False)
        result=assess(observed,dict(independently_identical=True))
        self.assertTrue(result['capture_ready'])
        self.assertFalse(result['control_ready'])
        self.assertFalse(result['pose_quality_passed'])
        self.assertFalse(result['release_authorized'])

    def test_invalid_input_cannot_authorize_capture(self):
        base=dict(views=1,state_unchanged=True,quality_passed=False,
                  release_authorized=False)
        for change in (dict(views=0),dict(state_unchanged=False),dict(release_authorized=True)):
            with self.subTest(change=change):
                self.assertFalse(assess(dict(base,**change),
                    dict(independently_identical=True))['capture_ready'])
        self.assertFalse(assess(base,dict(independently_identical=False))['capture_ready'])

    def test_valid_pose_still_cannot_enable_control(self):
        result=assess(dict(views=2,state_unchanged=True,quality_passed=True,
                          release_authorized=False),dict(independently_identical=True))
        self.assertTrue(result['pose_quality_passed'])
        self.assertFalse(result['control_ready'])
        self.assertFalse(result['release_authorized'])

    def test_rgb_digest_is_verified_but_not_cross_compared(self):
        with TemporaryDirectory() as temporary:
            folder=Path(temporary)
            self.write_fixture(folder)
            first=metadata(folder)
            self.write_fixture(folder,rgb=b'other quantized pixels')
            self.assertEqual(first,metadata(folder))
            (folder/'rgb.png').write_bytes(b'tampered')
            with self.assertRaises(AssertionError):
                metadata(folder)

    def test_sensor_tampering_is_rejected(self):
        with TemporaryDirectory() as temporary:
            folder=Path(temporary)
            self.write_fixture(folder)
            (folder/'sensor.npz').write_bytes(b'tampered')
            with self.assertRaises(AssertionError):
                metadata(folder)

    def write_fixture(self,folder,*,rgb=b'pixels'):
        (folder/'rgb.png').write_bytes(rgb)
        (folder/'sensor.npz').write_bytes(b'sensor')
        values=dict(rgb_sha256=hashlib.sha256(rgb).hexdigest(),
                    sensor_sha256=hashlib.sha256(b'sensor').hexdigest(),intrinsics=[1,2,3,4])
        (folder/'calibration.json').write_text(json.dumps(values),encoding='utf-8')
