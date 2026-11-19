from unittest.mock import patch


class CaptureComplete(BaseException):
    pass


def execute(backend,values,*,capture):
    _,env,planners,durations,_,dt=values
    assert len(planners)==3 and len(durations)==4 and durations[0]==0.
    start=float(env.mj_data.time)
    original=env.step
    seen=[]
    def step(*args,**kwargs):
        result=original(*args,**kwargs)
        if not seen and float(env.mj_data.time)-start>=durations[1]-.25*dt:
            seen.append('after_lift')
            capture('after_lift')
        return result
    with patch.object(env,'step',step):
        backend(*values)
    assert seen==['after_lift']
    capture('before_release')
    raise CaptureComplete('Observation-only protocol stops before release')
