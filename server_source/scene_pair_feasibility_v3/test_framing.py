"""完整入画不能用裁剪后的可见面积代替。"""
import importlib.util
import unittest


class FramingTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('sf_camera'), '缺少完整入画约束')
        return __import__('sf_camera')

    def test_optical_center_projects_to_image_center(self):
        module = self.module()
        camera = dict(position=[0., 0., 2.], rotation=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]], fovy=60.)
        pixels, depths = module.project([[0.,0.,0.]], camera)
        self.assertEqual([320., 320.], pixels[0].tolist())
        self.assertEqual(2., depths[0])

    def test_partial_object_and_behind_camera_are_rejected(self):
        module = self.module()
        camera = dict(position=[0.,0.,2.], rotation=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]], fovy=60.)
        inside = {'target':[[-.1,-.1,0.],[.1,.1,.1]]}
        partial = {'target':[[.8,-.1,0.],[1.4,.1,.1]]}
        behind = {'target':[[-.1,-.1,2.1],[.1,.1,2.2]]}
        self.assertTrue(module.framed(inside,camera)['passed'])
        self.assertFalse(module.framed(partial,camera)['passed'])
        self.assertFalse(module.framed(behind,camera)['passed'])

    def test_proposals_are_deterministic_and_remain_in_existing_ranges(self):
        module = self.module()
        boxes = {'target':[[.9,.1,.74],[1.5,1.1,.9]]}
        one = module.proposal(961103, 1, boxes=boxes)
        self.assertEqual(one, module.proposal(961103, 1, boxes=boxes))
        self.assertNotEqual(one, module.proposal(961103, 2, boxes=boxes))
        self.assertTrue(-60 <= one['azimuth_offset_deg'] <= 60)
        self.assertTrue(35 <= one['elevation_deg'] <= 75)
        self.assertTrue(48 <= one['fovy'] <= 65)


if __name__ == '__main__':
    unittest.main()
