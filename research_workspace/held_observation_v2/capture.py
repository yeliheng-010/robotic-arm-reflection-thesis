from unittest.mock import patch
from sd_runtime import render as raw_render
from held_observation_v1.capture import checkpoint as original_checkpoint


def checkpoint(env,case,*,folder,phase):
    with patch.object(env,'render',lambda:raw_render(env)):
        return original_checkpoint(env,case,folder=folder,phase=phase)
