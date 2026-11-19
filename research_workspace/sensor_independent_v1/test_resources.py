import unittest
from types import SimpleNamespace
from sensor_independent_v1.resources import geometry_resources


class ResourcesTests(unittest.TestCase):
    def test_create_at_zero_then_restore_original_before_use(self):
        model = SimpleNamespace(vis=SimpleNamespace(quality=SimpleNamespace(offsamples=4)))
        observed, closed = [], []
        def factory():
            observed.append(model.vis.quality.offsamples)
            return SimpleNamespace(close=lambda: closed.append(True))
        with geometry_resources(model, [factory, factory]) as resources:
            self.assertEqual([0, 0], observed)
            self.assertEqual(2, len(resources))
            self.assertEqual(4, model.vis.quality.offsamples)
        self.assertEqual([True, True], closed)

    def test_factory_failure_restores_and_closes_prior_resource(self):
        model = SimpleNamespace(vis=SimpleNamespace(quality=SimpleNamespace(offsamples=4)))
        closed = []
        def bad():
            raise RuntimeError('allocation failure')
        with self.assertRaisesRegex(RuntimeError, 'allocation failure'):
            with geometry_resources(model, [lambda: SimpleNamespace(close=lambda: closed.append(True)), bad]):
                pass
        self.assertEqual(4, model.vis.quality.offsamples)
        self.assertEqual([True], closed)

    def test_usage_failure_also_releases_resources(self):
        model = SimpleNamespace(vis=SimpleNamespace(quality=SimpleNamespace(offsamples=4)))
        closed = []
        with self.assertRaisesRegex(RuntimeError, 'capture failed'):
            with geometry_resources(model, [lambda: SimpleNamespace(close=lambda: closed.append(True))]):
                raise RuntimeError('capture failed')
        self.assertEqual(4, model.vis.quality.offsamples)
        self.assertEqual([True], closed)


if __name__ == '__main__':
    unittest.main()
