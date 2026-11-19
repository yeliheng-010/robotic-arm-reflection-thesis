"""用现有落箱判据的内尺寸约束预测物体外接盒，而非仅约束TCP。"""
import numpy as np
import mujoco
from reflection.monitors import object_extents
from goal_policy import usable_half, GRID, BOTTOM_GAPS_M

PREFIXES={'BlueBin':'blue_bin','RedBin':'red_bin','SortingTray':'sorting_tray'}


def geometry(flow, item):
    model,data=flow.env.mj_model,flow.env.mj_data
    prefix=PREFIXES[item['destination']]
    floor=model.geom(prefix+'_floor').id
    wall=model.geom(prefix+'_left_wall').id
    np.testing.assert_allclose(data.geom_xmat[floor].reshape(3,3),np.eye(3),atol=1e-12)
    thickness=.008 if item['destination']=='SortingTray' else .012
    interior=model.geom_size[floor,:2]-thickness
    low,high=object_extents(model,data,model.body(item['source']).id)
    center,extent=(low+high)/2,(high-low)/2
    usable=usable_half(interior,extent[:2])
    return dict(source_center=center.tolist(),source_half=extent.tolist(),
                bin_center=data.geom_xpos[floor].tolist(),interior_half=interior.tolist(),
                usable_half=usable,wall_top=float(data.geom_xpos[wall,2]+model.geom_size[wall,2]))


def targets(pose, geometry):
    extent=np.array(geometry['source_half'])
    offset=pose.t-np.array(geometry['source_center'])
    for grid_index,grid in enumerate(GRID):
        for gap in BOTTOM_GAPS_M:
            center=np.array(geometry['bin_center'])
            center[:2]+=np.array(grid)*geometry['usable_half']
            center[2]=geometry['wall_top']+gap+extent[2]
            yield dict(id=f'g{grid_index}_h{gap}',target=(center+offset).tolist(),
                       object_center=center.tolist(),bottom_gap=gap,grid=list(grid))
