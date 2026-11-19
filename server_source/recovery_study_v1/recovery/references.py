"""加载只读的已冻结场景实现。"""
import importlib.util
from pathlib import Path
import sys

BASE = Path('/home/yeliheng/grasp_server')
SCENES = BASE/'scene_qualification_v1'
sys.path.insert(0,str(SCENES))
try:
    spec = importlib.util.spec_from_file_location('qualified_scene_protocol',SCENES/'protocol.py')
    scene_protocol = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scene_protocol)
    scene_build = scene_protocol.build
    scene_items = scene_protocol.items
finally:
    sys.path.remove(str(SCENES))

collision_context = scene_protocol.reference.context
