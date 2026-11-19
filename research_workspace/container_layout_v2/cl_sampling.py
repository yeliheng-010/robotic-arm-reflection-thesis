"""与逐个包围盒检查等价的向量化拒绝采样，不改变布局分布。"""
import numpy as np
from cl_design import CONTAINERS, CLEARANCE, MIN_MOVE


def moved_boxes(batch, geometry):
    count=len(batch)
    boxes={name:np.broadcast_to(value,(count,2,3)).copy()
           for name,value in geometry['boxes'].items()}
    for index,name in enumerate(CONTAINERS):
        delta=batch[:,index]-geometry['centers'][name][:2]
        boxes[name][:,:,:2]+=delta[:,None,:]
    return boxes


def valid_candidates(batch, geometry):
    boxes=moved_boxes(batch,geometry)
    table=np.array(geometry['table'])
    valid=np.ones(len(batch),dtype=bool)
    changed=np.zeros(len(batch),dtype=bool)
    for index,name in enumerate(CONTAINERS):
        low,high=boxes[name][:,0],boxes[name][:,1]
        valid &= np.all(low[:,:2]>=table[0,:2]+CLEARANCE,axis=1)
        valid &= np.all(high[:,:2]<=table[1,:2]-CLEARANCE,axis=1)
        valid &= np.linalg.norm(batch[:,index]-geometry['centers'][name][:2],axis=1)>=MIN_MOVE
        for other,box in boxes.items():
            if other in (name,'simple_table'):
                continue
            gap=np.max(np.maximum(low-box[:,1],box[:,0]-high),axis=1)
            valid &= gap>=CLEARANCE
        for other_index in range(index+1,len(CONTAINERS)):
            other=CONTAINERS[other_index]
            old=np.array(geometry['centers'][name][:2])-geometry['centers'][other][:2]
            changed |= np.any((batch[:,index]-batch[:,other_index])*old<0,axis=1)
    return valid & changed
