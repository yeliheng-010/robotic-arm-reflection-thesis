"""感知真值工具：基于 MuJoCo 分割渲染与接触信息。

检测器使用仿真分割、接触物体身份和位姿残差等真值辅助证据。
指垫接触可对应真机触觉/电流信号，但当前实现并非纯视觉真机检测。
最终评估独立检查物理包含、支撑和稳定性，不采用规划器自报的成功标志。
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

import mujoco
import numpy as np


PAD_GEOMS = ("left_pad1", "left_pad2", "right_pad1", "right_pad2")
LEFT_PAD_GEOMS = ("left_pad1", "left_pad2")
RIGHT_PAD_GEOMS = ("right_pad1", "right_pad2")

# 机器人本体（机械臂 + 夹爪）的根 body，用于把接触划分为"机器人-环境"
ROBOT_ROOT_BODIES = ("ur5e_base", "2f85_base")
# 桌面/地面等允许接触的静态支撑物
SUPPORT_BODY_PREFIXES = ("world", "table1", "table2", "simple_table")


def body_id(model: mujoco.MjModel, name: str) -> int:
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


def body_name(model: mujoco.MjModel, bid: int) -> str:
    return mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, bid) or f"body{bid}"


def root_name_of_geom(model: mujoco.MjModel, gid: int) -> str:
    return body_name(model, int(model.body_rootid[model.geom_bodyid[gid]]))


def robot_root_ids(model: mujoco.MjModel) -> Set[int]:
    return {body_id(model, n) for n in ROBOT_ROOT_BODIES if body_id(model, n) >= 0}


def pad_contacts(model: mujoco.MjModel, data: mujoco.MjData) -> Dict[str, Set[str]]:
    """返回左右指垫分别接触到的根物体名称。"""
    left = {mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n) for n in LEFT_PAD_GEOMS}
    right = {mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n) for n in RIGHT_PAD_GEOMS}
    robot = robot_root_ids(model)
    touched = {"left": set(), "right": set()}
    for c in data.contact[: data.ncon]:
        for pad_side, pad_ids in (("left", left), ("right", right)):
            if c.geom1 in pad_ids or c.geom2 in pad_ids:
                other = c.geom2 if c.geom1 in pad_ids else c.geom1
                root = int(model.body_rootid[model.geom_bodyid[other]])
                if root not in robot:
                    touched[pad_side].add(body_name(model, root))
    return touched


def grasped_objects(model: mujoco.MjModel, data: mujoco.MjData) -> Set[str]:
    """左右指垫同时接触的物体，视为被夹持的物体。"""
    touched = pad_contacts(model, data)
    return touched["left"] & touched["right"]


def robot_environment_contacts(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    ignore: Iterable[str] = (),
) -> List[Tuple[str, str]]:
    """机器人本体与环境物体之间的接触（不含被夹持物体、支撑面）。"""
    robot = robot_root_ids(model)
    ignore = set(ignore)
    pairs = []
    for c in data.contact[: data.ncon]:
        r1 = int(model.body_rootid[model.geom_bodyid[c.geom1]])
        r2 = int(model.body_rootid[model.geom_bodyid[c.geom2]])
        if (r1 in robot) == (r2 in robot):
            continue
        robot_side, env_side = (r1, r2) if r1 in robot else (r2, r1)
        env_name = body_name(model, env_side)
        if env_name in ignore or env_name.startswith(SUPPORT_BODY_PREFIXES):
            continue
        pairs.append((body_name(model, robot_side), env_name))
    return pairs


def held_object_contacts(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    held: str,
    ignore: Iterable[str] = (),
) -> List[str]:
    """被夹持物体与环境（非机器人）之间的接触，用于检测搬运中物体撞到障碍。"""
    hid = body_id(model, held)
    robot = robot_root_ids(model)
    ignore = set(ignore)
    hits = []
    for c in data.contact[: data.ncon]:
        r1 = int(model.body_rootid[model.geom_bodyid[c.geom1]])
        r2 = int(model.body_rootid[model.geom_bodyid[c.geom2]])
        if hid not in (r1, r2):
            continue
        other = r2 if r1 == hid else r1
        if other in robot:
            continue
        name = body_name(model, other)
        if name in ignore or name.startswith(SUPPORT_BODY_PREFIXES):
            continue
        hits.append(name)
    return hits


class SegmentationRenderer:
    """渲染相机视角下每个像素所属的根物体，用于判定视觉定位点落在哪个物体上。"""

    def __init__(self, model: mujoco.MjModel, height: int, width: int, camera: str = "cam"):
        self.model = model
        self.camera = camera
        self.renderer = mujoco.Renderer(model, height=height, width=width)
        self.renderer.enable_segmentation_rendering()

    def root_map(self, data: mujoco.MjData) -> np.ndarray:
        """返回 HxW 的根 body id 图，背景为 -1。"""
        self.renderer.update_scene(data, self.camera)
        seg = self.renderer.render()
        obj_ids = seg[..., 0]
        obj_types = seg[..., 1]
        out = np.full(obj_ids.shape, -1, dtype=np.int32)
        is_geom = (obj_types == int(mujoco.mjtObj.mjOBJ_GEOM)) & (obj_ids >= 0)
        out[is_geom] = self.model.body_rootid[self.model.geom_bodyid[obj_ids[is_geom]]]
        return out

    def object_at(self, data: mujoco.MjData, pixel: Tuple[int, int], win: int = 3) -> Optional[str]:
        """定位点附近像素中出现最多的根物体名称。"""
        root = self.root_map(data)
        h, w = root.shape
        u, v = int(pixel[0]), int(pixel[1])
        patch = root[max(0, v - win): min(h, v + win + 1), max(0, u - win): min(w, u + win + 1)]
        patch = patch[patch >= 0]
        if patch.size == 0:
            return None
        values, counts = np.unique(patch, return_counts=True)
        return body_name(self.model, int(values[np.argmax(counts)]))

    def close(self):
        from manipulator_grasp.utils.mj import close_renderer
        close_renderer(self.renderer)


def project_to_pixel(env, point_world: np.ndarray) -> Tuple[int, int]:
    """世界坐标 → 相机像素坐标（与 grasp_process.camera_calibration_from_env 一致）。"""
    from grasp_process import camera_calibration_from_env

    T, K = camera_calibration_from_env(env)
    pc = np.asarray(T.inv() * np.asarray(point_world, dtype=np.float64)).reshape(3)
    return int(round(K[0] * pc[0] / pc[2] + K[2])), int(round(K[1] * pc[1] / pc[2] + K[3]))


def body_up_axis_tilt_deg(model: mujoco.MjModel, data: mujoco.MjData, name: str, initial_quat: np.ndarray) -> float:
    """物体当前姿态相对初始姿态的倾斜角（度），用于判定是否倾倒。"""
    bid = body_id(model, name)
    R0 = np.zeros(9)
    mujoco.mju_quat2Mat(R0, initial_quat)
    R1 = data.xmat[bid]
    z0 = R0.reshape(3, 3)[:, 2]
    z1 = R1.reshape(3, 3)[:, 2]
    cos = float(np.clip(np.dot(z0, z1), -1.0, 1.0))
    return float(np.degrees(np.arccos(cos)))
