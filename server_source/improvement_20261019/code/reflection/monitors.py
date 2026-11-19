"""Stage monitors. Segmentation and placement checks explicitly use simulator truth."""
import json

import mujoco
import numpy as np

from .errors import ErrorReport, ErrorType, TaskAbort
from .sim_sensing import grasped_objects, held_object_contacts, robot_environment_contacts, body_up_axis_tilt_deg


def abort(kind, message, **evidence):
    raise TaskAbort(ErrorReport(kind, message, evidence, detector="mujoco_monitor"))


def validate_plan(plan, source, destination, resolve):
    if isinstance(plan, str):
        try:
            plan = json.loads(plan)
        except (TypeError, ValueError) as exc:
            abort(ErrorType.PLAN_PARSE_ERROR, str(exc))
    actions = plan.get("action_components") if isinstance(plan, dict) else None
    if not isinstance(actions, list) or any(not isinstance(a, dict) for a in actions):
        abort(ErrorType.PLAN_PARSE_ERROR, "action_components must be a list of objects")
    expected = ["move_to_grasp_pose", "close_gripper", "move_to_point", "open_gripper", "back_to_zero"]
    if [a.get("action") for a in actions] != expected:
        abort(ErrorType.PLAN_SEQUENCE_INVALID, "Expected one complete pick-and-place sequence", actions=actions)
    for index, body in ((0, source), (1, source), (2, destination)):
        component = actions[index].get("component")
        if not isinstance(component, list) or len(component) != 2:
            abort(ErrorType.PLAN_TARGET_MISSING, "Missing object and part", action_index=index)
        if any(not isinstance(value, str) or not value.strip() for value in component):
            abort(ErrorType.PLAN_PARSE_ERROR, "Object and part must be non-empty strings", action_index=index)
        resolved = resolve(component[0])
        if resolved is None:
            abort(ErrorType.PLAN_TARGET_MISSING, "Object is absent from scene", object=component[0])
        if resolved != body:
            abort(ErrorType.PLAN_WRONG_OBJECT, "Planned object differs from requested task", expected=body, actual=resolved)
        if not isinstance(actions[index].get("args", {}), dict):
            abort(ErrorType.PLAN_PARSE_ERROR, "Action args must be an object", action_index=index)
    return actions


def validate_grounding(pixel, depth, root_map, expected_id):
    if not isinstance(pixel, (tuple, list)) or len(pixel) != 2:
        abort(ErrorType.GROUNDING_OUT_OF_IMAGE, "Missing two-dimensional grounding point", pixel=pixel)
    if any(isinstance(v, bool) or not isinstance(v, (int, float, np.integer)) or not np.isfinite(v) for v in pixel):
        abort(ErrorType.GROUNDING_OUT_OF_IMAGE, "Invalid grounding coordinates", pixel=str(pixel))
    u, v = map(int, pixel)
    h, w = depth.shape
    if not 0 <= u < w or not 0 <= v < h:
        abort(ErrorType.GROUNDING_OUT_OF_IMAGE, "Pixel is outside image", pixel=[u, v])
    patch = root_map[max(v-3, 0):v+4, max(u-3, 0):u+4]
    if not np.any(patch == expected_id):
        abort(ErrorType.GROUNDING_OFF_TARGET, "Pixel belongs to a different scene object", pixel=[u, v],
              observed_body_id=int(root_map[v, u]), expected_body_id=int(expected_id), signal_source="simulation_segmentation")
    if not np.isfinite(depth[v, u]) or depth[v, u] <= 0:
        abort(ErrorType.DEPTH_INVALID, "Non-positive or non-finite depth", pixel=[u, v])
    return u, v


def validate_mask(mask, root_map, expected_id):
    if mask is None or mask.shape != root_map.shape:
        abort(ErrorType.MASK_INVALID, "Mask is missing or has wrong dimensions")
    active = mask > 0
    count = int(active.sum())
    if count < 15 or count > mask.size * 0.35:
        abort(ErrorType.MASK_INVALID, "Unexpected mask area", pixels=count)
    overlap = float(np.count_nonzero(active & (root_map == expected_id)) / count)
    if overlap < 0.5:
        abort(ErrorType.MASK_INVALID, "Mask mostly covers a different object", target_overlap=overlap,
              signal_source="simulation_segmentation")


class ExecutionMonitor:
    def __init__(self, env, source, destination):
        self.env, self.source, self.destination = env, source, destination
        self.phase = "idle"
        self.missing_steps = 0

    def check_grasp(self, residual):
        held = grasped_objects(self.env.mj_model, self.env.mj_data)
        if self.source not in held:
            kind = ErrorType.WRONG_OBJECT_GRASPED if held else ErrorType.EMPTY_GRASP
            abort(kind, "Target is not held by both finger pads", held=sorted(held),
                  closure=float(self.env.mj_data.joint("right_driver_joint").qpos[0]),
                  grasp_residual_xy=list(map(float, residual)), signal_source="simulation_pad_contacts")

    def tick(self):
        if self.phase != "carry":
            return
        m, d = self.env.mj_model, self.env.mj_data
        ignore = (self.source, self.destination)
        hits = robot_environment_contacts(m, d, ignore=ignore)
        hits += [(self.source, name) for name in held_object_contacts(m, d, self.source, ignore=(self.destination,))]
        if hits:
            abort(ErrorType.COLLISION, "Unexpected contact while carrying target", contacts=hits,
                  signal_source="simulation_contacts")
        if self.source in grasped_objects(m, d):
            self.missing_steps = 0
        else:
            self.missing_steps += 10
            if self.missing_steps >= 100:
                abort(ErrorType.OBJECT_DROPPED, "Lost bilateral target contact for 0.2 simulation seconds",
                      missing_steps=self.missing_steps, signal_source="simulation_pad_contacts")


def object_extents(model, data, bid):
    gids = np.flatnonzero(model.geom_bodyid == bid)
    lows, highs = [], []
    for gid in gids:
        size = model.geom_size[gid]
        typ = int(model.geom_type[gid])
        if typ == int(mujoco.mjtGeom.mjGEOM_SPHERE):
            half = np.repeat(size[0], 3)
        elif typ in (int(mujoco.mjtGeom.mjGEOM_CYLINDER), int(mujoco.mjtGeom.mjGEOM_CAPSULE)):
            half = np.array([size[0], size[0], size[1] + (size[0] if typ == int(mujoco.mjtGeom.mjGEOM_CAPSULE) else 0)])
        elif typ == int(mujoco.mjtGeom.mjGEOM_BOX):
            half = size
        else:
            half = np.repeat(model.geom_rbound[gid], 3)
        extent = np.abs(data.geom_xmat[gid].reshape(3, 3)) @ half
        lows.append(data.geom_xpos[gid] - extent)
        highs.append(data.geom_xpos[gid] + extent)
    return np.min(lows, axis=0), np.max(highs, axis=0)


def evaluate_placement(env, source, destination, initial_quat):
    m, d = env.mj_model, env.mj_data
    bid, dst = m.body(source).id, m.body(destination).id
    prefix = {"BlueBin": "blue_bin", "RedBin": "red_bin", "SortingTray": "sorting_tray"}[destination]
    floor = m.geom(prefix + "_floor").id
    center = d.geom_xpos[floor]
    low, high = object_extents(m, d, bid)
    interior_half = m.geom_size[floor, :2] - (0.012 if destination != "SortingTray" else 0.008)
    inside_xy = bool(np.all(low[:2] >= center[:2]-interior_half) and np.all(high[:2] <= center[:2]+interior_half))
    wall = m.geom(prefix + "_left_wall").id
    floor_top = float(center[2] + m.geom_size[floor, 2])
    wall_top = float(d.geom_xpos[wall, 2] + m.geom_size[wall, 2])
    supported = any(
        {int(m.body_rootid[m.geom_bodyid[c.geom1]]), int(m.body_rootid[m.geom_bodyid[c.geom2]])} == {bid, dst}
        for c in d.contact[:d.ncon])
    settled = bool(np.linalg.norm(d.qvel[m.jnt_dofadr[m.body_jntadr[bid]]:m.jnt_dofadr[m.body_jntadr[bid]]+3]) < 0.05)
    inside_z = bool(low[2] >= floor_top-0.015 and d.xpos[bid, 2] <= wall_top+0.02)
    tilt = body_up_axis_tilt_deg(m, d, source, initial_quat)
    upright = source != "GreenCylinder" or tilt <= 45
    residual = d.xpos[bid, :2] - d.xpos[dst, :2]
    evidence = {"position": d.xpos[bid].tolist(), "placement_residual_xy": residual.tolist(),
                "xy_error_m": float(np.linalg.norm(residual)), "inside_xy": inside_xy,
                "inside_z": inside_z, "supported": supported, "settled": settled,
                "tilt_deg": tilt, "signal_source": "simulation_ground_truth"}
    success = inside_xy and inside_z and supported and settled and upright
    if success:
        return True, evidence, None
    kind = ErrorType.OBJECT_TOPPLED if not upright else ErrorType.OBJECT_OUTSIDE_CONTAINER
    return False, evidence, ErrorReport(kind, "Final object does not satisfy physical containment and stability", evidence,
                                       detector="independent_simulation_evaluator")


def verify_visual(client, before, after, instruction):
    result = client.ask_json(
        f"First image: before. Second image: after. Task: {instruction}. "
        "Judge visible evidence only. Return JSON {\"success\":true/false/null,\"reason\":str}. "
        "Use null if occlusion prevents judgment. A gripper above a bin alone does not prove success.",
        images=[before, after], max_tokens=500, cache_tag="verify-v1")
    if "success" not in result or (result["success"] is not None and type(result["success"]) is not bool):
        raise ValueError("Visual verification must return boolean or null")
    if not isinstance(result.get("reason"), str):
        raise ValueError("Visual verification must include reason")
    return result
