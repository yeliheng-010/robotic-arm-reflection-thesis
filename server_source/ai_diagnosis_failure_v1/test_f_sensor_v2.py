from copy import deepcopy
import unittest
from f_sensor_v2 import repeated, RGB_NOT_SENT


def fixture():
    public = [{'time_s': 12.} for _ in range(3)]
    private = [dict(state_sha256='same', clean_sha256='same', noisy_sha256=str(i), rgb_sha256=str(i))
               for i in range(3)]
    return public, private


class SensorRevisionTests(unittest.TestCase):
    def test_rgb_difference_permitted_only_when_not_model_input(self):
        public, private = fixture()
        value = repeated(public, private, sensing={'rgb': RGB_NOT_SENT})
        self.assertFalse(value['rgb_bitwise_identical'])
        with self.assertRaises(AssertionError):
            repeated(public, private, sensing={'rgb': 'attached'})

    def test_state_and_clean_depth_still_require_exact_identity(self):
        public, private = fixture()
        for key in ('state_sha256', 'clean_sha256'):
            changed = deepcopy(private)
            changed[1][key] = 'tampered'
            with self.assertRaises(AssertionError):
                repeated(public, changed, sensing={'rgb': RGB_NOT_SENT})

    def test_reused_noise_is_rejected(self):
        public, private = fixture()
        private[1]['noisy_sha256'] = private[0]['noisy_sha256']
        with self.assertRaises(AssertionError):
            repeated(public, private, sensing={'rgb': RGB_NOT_SENT})

    def test_advanced_time_is_rejected(self):
        public, private = fixture()
        public[1]['time_s'] += .002
        with self.assertRaises(AssertionError):
            repeated(public, private, sensing={'rgb': RGB_NOT_SENT})


if __name__ == '__main__':
    unittest.main()
