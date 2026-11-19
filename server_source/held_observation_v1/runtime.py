from unittest.mock import patch
from qa_runtime import PlanningComplete
import surface_physical_v1.runtime as original
import surface_physical_v1.held as held
from held_observation_v1.pause import execute
from held_observation_v1.capture import checkpoint

ORIGINAL_SELECT=original.selecting
ORIGINAL_CHECK=held.check_and_run


def selecting(session):
    choose=ORIGINAL_SELECT(session)
    def wrapped(flow,**kwargs):
        try:
            return choose(flow,**kwargs)
        except PlanningComplete:
            checkpoint(flow.env,session.case,folder=session.folder/'checkpoints/preflight',phase='preflight')
            raise
    return wrapped


class PreviewSession(original.PreviewSession):
    def _engine(self):
        with patch.object(original,'selecting',selecting):
            super()._engine()


class Session(original.Session):
    def _engine(self):
        def observed(backend,values,*,trace,folder):
            def capture(phase):
                return checkpoint(values[1],self.case,folder=self.folder/'checkpoints'/phase,phase=phase)
            def watched(*args):
                return execute(backend,args,capture=capture)
            return ORIGINAL_CHECK(watched,values,trace=trace,folder=folder)
        with patch.object(held,'check_and_run',observed):
            super()._engine()
