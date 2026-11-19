import unittest
from common import visible


class QualificationTests(unittest.TestCase):
    def test_hidden_and_small_target_rejected(self):
        self.assertFalse(visible(dict(pixels=0, visible_fraction=0.)))
        self.assertFalse(visible(dict(pixels=63, visible_fraction=1.)))

    def test_occlusion_and_boundary(self):
        self.assertFalse(visible(dict(pixels=1000, visible_fraction=.699)))
        self.assertTrue(visible(dict(pixels=64, visible_fraction=.70)))
