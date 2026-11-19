"""只在恢复状态上选视角；遮挡归属仅作为私有工程证据。"""
import numpy as np
from cv_select import evaluate, image
from cv_metrics import isolated_mask
from sf_camera import framed
from proposals import cameras


def rank(rows):
    valid = [row for row in rows if 'gate' in row]
    def score(row):
        fractions = [v.get('visible_fraction',0.) for v in row['gate']['objects'].values()]
        return len(row['gate']['rejected']), -min(fractions), row.get('index',0)
    return sorted(valid,key=score)[:3]


def occluders(env, renderer, report):
    roots = renderer.root_map(env.mj_data)
    output = {}
    for name in report['gate']['rejected']:
        outline = isolated_mask(env,renderer,name)
        body = env.mj_model.body(name).id
        values, counts = np.unique(roots[outline & (roots != body)],return_counts=True)
        blocked = {env.mj_model.body(int(v)).name if v>=0 else 'unassigned':int(c)
            for v,c in zip(values,counts)}
        output[name] = dict(isolated_pixels=int(outline.sum()),blocked_pixels_by_root=blocked)
    return output


def search(env, renderer, spec, *, boxes, folder, anchors, previous):
    attempts, selected = [], None
    proposals = cameras(anchors,boxes,previous=previous)
    for index, camera in enumerate(proposals):
        if framed(boxes,camera)['passed']:
            row = evaluate(env,renderer,camera,boxes=boxes)
        else:
            row = dict(accepted=False,status='framing_rejected')
        attempts.append(dict(row,index=index,camera=camera))
        if row['accepted']:
            selected = camera
            image(env,folder/'after.png')
            break
    return dict(name=spec['name'],accepted=selected is not None,selected=selected,
        attempts=attempts,proposed=len(proposals),checked=len(attempts),
        unchanged_state=True,physical_attempts=0,training_eligible=False,
        scope='snapshot_camera_qualification_only')
