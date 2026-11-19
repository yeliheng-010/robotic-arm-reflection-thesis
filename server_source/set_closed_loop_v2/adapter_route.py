"""串行服务的模型切换：退出或异常均恢复原adapter。"""
from contextlib import contextmanager, nullcontext

ADAPTERS = {'previous159': 'previous159', 'new189': 'new189'}


@contextmanager
def activate(model, method):
    if method not in ('base', *ADAPTERS):
        raise ValueError('Unknown model method: ' + method)
    previous = model.active_adapter
    try:
        if method != 'base':
            model.set_adapter(ADAPTERS[method])
            assert model.active_adapter == ADAPTERS[method]
        model.eval()
        context = model.disable_adapter() if method == 'base' else nullcontext()
        with context:
            yield
    finally:
        model.set_adapter(previous)
        model.eval()
