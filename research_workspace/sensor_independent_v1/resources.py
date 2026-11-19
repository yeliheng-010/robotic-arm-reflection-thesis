"""独立创建几何渲染资源，不持久改变模型渲染参数。"""
from contextlib import contextmanager, ExitStack


@contextmanager
def geometry_resources(model, factories):
    original = model.vis.quality.offsamples
    with ExitStack() as stack:
        resources = []
        try:
            model.vis.quality.offsamples = 0
            for factory in factories:
                resource = factory()
                stack.callback(resource.close)
                resources.append(resource)
        finally:
            model.vis.quality.offsamples = original
        yield resources
