from types import SimpleNamespace
from unittest.mock import Mock
import unittest
from f_stop import stop_after, EngineeringStop


class StopTests(unittest.TestCase):
    def test_stops_only_after_original_finishes(self):
        original, trace = Mock(), {}
        flow = SimpleNamespace(env=SimpleNamespace(mj_data=SimpleNamespace(time=12.)))
        with self.assertRaises(EngineeringStop):
            stop_after(original, trace)(flow, target=(1, 2, 3))
        original.assert_called_once_with(flow, target=(1, 2, 3))
        self.assertTrue(trace['triggered'])
        self.assertFalse(trace['natural_failure'])

    def test_natural_error_is_not_replaced(self):
        original, trace = Mock(side_effect=ValueError('original_failure')), {}
        with self.assertRaisesRegex(ValueError, 'original_failure'):
            stop_after(original, trace)(None)
        self.assertNotIn('triggered', trace)


if __name__ == '__main__':
    unittest.main()
