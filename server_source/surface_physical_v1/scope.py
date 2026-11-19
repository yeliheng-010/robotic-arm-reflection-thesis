from contextvars import ContextVar
COLLECTING=ContextVar('surface_collecting',default=False)


def collection(original):
    def plans(*args,**kwargs):
        token=COLLECTING.set(True)
        try:
            return original(*args,**kwargs)
        finally:
            COLLECTING.reset(token)
    return plans
