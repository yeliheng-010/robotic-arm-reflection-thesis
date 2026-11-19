import json
from pathlib import Path
import mujoco
import numpy as np
from reflection.monitors import object_extents
root=Path('/home/yeliheng/grasp_server')
model=mujoco.MjModel.from_xml_path(str(root/'improvement_20261019/code/manipulator_grasp/assets/scenes/scene.xml'))
data=mujoco.MjData(model)
record=json.loads((root/'refinement_v2/collision/24_0/result.json').read_text())['records'][0]
data.qpos[:]=record['candidate_trace']['initial_qpos']
mujoco.mj_forward(model,data)
rows=[]
for i in range(1,model.nbody):
    if model.body(i).geomnum==0: continue
    low,high=object_extents(model,data,i)
    if high[0]<1.1 or low[0]>1.55 or high[1]<.55 or low[1]>.93 or high[2]<.745 or low[2]>1.2: continue
    rows.append(dict(body=model.body(i).name,low=low.tolist(),high=high.tolist(),dynamic=bool(model.body(i).jntnum)))
print(json.dumps(rows))
