import os
import sys
import cv2
import numpy as np
import torch
import open3d as o3d
from PIL import Image
import spatialmath as sm
import time

from manipulator_grasp.arm.motion_planning import *

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, 'graspnet-baseline', 'graspnetAPI'))
from graspnetAPI import GraspGroup

sys.path.append(os.path.join(ROOT_DIR, 'graspnet-baseline', 'models'))
sys.path.append(os.path.join(ROOT_DIR, 'graspnet-baseline', 'dataset'))
sys.path.append(os.path.join(ROOT_DIR, 'graspnet-baseline', 'utils'))
sys.path.append(os.path.join(ROOT_DIR, 'manipulator_grasp'))

from collision_detector import ModelFreeCollisionDetector
from data_utils import CameraInfo, create_point_cloud_from_depth_image


_NET_CACHE = {}


#网络加载
def get_net():
    """
    加载训练好的 GraspNet 模型
    """
    from graspnet import GraspNet

    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    cache_key = str(device)
    if cache_key in _NET_CACHE:
        return _NET_CACHE[cache_key]

    net = GraspNet(input_feature_dim=0,
                   num_view=300, 
                   num_angle=12, 
                   num_depth=4,
                   cylinder_radius=0.05, 
                   hmin=-0.02, 
                   hmax_list=[0.01, 0.02, 0.03, 0.04], 
                   is_training=False)
    net.to(device)
    # The released checkpoint was saved from CUDA.  Map it to the device used
    # by the model so the project can also start on CPU-only hosts.
    checkpoint = torch.load('./logs/log_rs/checkpoint-rs.tar', map_location=device) # checkpoint_path
    net.load_state_dict(checkpoint['model_state_dict'])
    net.eval()
    _NET_CACHE[cache_key] = net
    return net


def _load_image_or_array(value, *, name):
    if isinstance(value, str):
        return np.array(Image.open(value))
    if isinstance(value, np.ndarray):
        return value
    raise TypeError(f"{name} 既不是文件路径也不是 NumPy 数组")


def _sample_rows(rng, values, count):
    """固定随机种子的行采样；样本不足时按官方 baseline 的方式重复补足。"""
    if len(values) == 0:
        raise ValueError("无法从空点云采样")
    indices = rng.choice(len(values), size=count, replace=len(values) < count)
    return values[indices], indices


def _to_open3d_cloud(points, colors):
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points.astype(np.float32))
    cloud.colors = o3d.utility.Vector3dVector(colors.astype(np.float32))
    return cloud


# 目标感知采样：保留目标密度，同时加入场景上下文供碰撞判断和网络推理。
def get_and_process_data(
    color_path,
    depth_path,
    mask_path,
    *,
    num_points=20000,
    target_ratio=0.65,
    max_depth=2.0,
    random_seed=42,
    fovy=np.pi / 4,
):
    """
    根据给定的 RGB 图、深度图、掩码图（可以是 文件路径 或 NumPy 数组），生成输入点云及其它必要数据
    """
    color = _load_image_or_array(color_path, name="color_path").astype(np.float32)
    if color.max(initial=0.0) > 1.0:
        color /= 255.0
    depth = _load_image_or_array(depth_path, name="depth_path").astype(np.float32)
    target_mask = _load_image_or_array(mask_path, name="mask_path")
    if target_mask.ndim == 3:
        target_mask = target_mask[..., 0]

    if color.shape[:2] != depth.shape[:2] or depth.shape[:2] != target_mask.shape[:2]:
        raise ValueError(
            f"RGB/深度/掩码尺寸不一致: {color.shape[:2]}, {depth.shape[:2]}, {target_mask.shape[:2]}"
        )

    # 构造相机内参矩阵
    height = color.shape[0]
    width = color.shape[1]
    focal = height / (2.0 * np.tan(float(fovy) / 2.0))
    c_x = width / 2.0   # 水平中心
    c_y = height / 2.0  # 垂直中心
    intrinsic = np.array([
        [focal, 0.0, c_x],    
        [0.0, focal, c_y],   
        [0.0, 0.0, 1.0]
    ])
    factor_depth = 1.0  # 深度因子，根据实际数据调整

    # 利用深度图生成点云 (H,W,3) 并保留组织结构
    camera = CameraInfo(width, height, intrinsic[0][0], intrinsic[1][1], intrinsic[0][2], intrinsic[1][2], factor_depth)
    cloud = create_point_cloud_from_depth_image(depth, camera, organized=True)

    valid_depth = np.isfinite(depth) & (depth > 0.05) & (depth < float(max_depth))
    target_pixels = (target_mask > 0) & valid_depth
    scene_pixels = valid_depth
    context_pixels = scene_pixels & ~target_pixels

    target_points = cloud[target_pixels]
    target_colors = color[target_pixels]
    scene_points = cloud[scene_pixels]
    scene_colors = color[scene_pixels]
    context_points = cloud[context_pixels]
    context_colors = color[context_pixels]

    if len(target_points) < 64:
        raise ValueError(f"目标掩码有效点过少: {len(target_points)}，拒绝生成不可靠抓取")

    rng = np.random.default_rng(random_seed)
    target_count = int(round(num_points * float(target_ratio)))
    context_count = int(num_points) - target_count
    sampled_target, target_indices = _sample_rows(rng, target_points, target_count)
    sampled_target_colors = target_colors[target_indices]

    context_source = context_points if len(context_points) else scene_points
    context_color_source = context_colors if len(context_colors) else scene_colors
    sampled_context, context_indices = _sample_rows(rng, context_source, context_count)
    sampled_context_colors = context_color_source[context_indices]

    cloud_sampled = np.concatenate([sampled_target, sampled_context], axis=0)
    color_sampled = np.concatenate([sampled_target_colors, sampled_context_colors], axis=0)
    order = rng.permutation(len(cloud_sampled))
    cloud_sampled = cloud_sampled[order]
    color_sampled = color_sampled[order]
    sampled_count = len(cloud_sampled)

    target_cloud_o3d = _to_open3d_cloud(target_points, target_colors)
    scene_cloud_o3d = _to_open3d_cloud(scene_points, scene_colors)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    cloud_sampled = torch.from_numpy(cloud_sampled[np.newaxis].astype(np.float32)).to(device)
    # end_points = {'point_clouds': cloud_sampled}

    end_points = dict()
    end_points['point_clouds'] = cloud_sampled
    end_points['cloud_colors'] = color_sampled

    print(
        f"[INFO] 点云采样: 目标原始={len(target_points)}, 场景原始={len(scene_points)}, "
        f"网络输入={sampled_count} (目标占比={target_ratio:.0%})"
    )
    return end_points, target_cloud_o3d, scene_cloud_o3d, (target_mask > 0), depth


def _camera_intrinsics(height, width, fovy=np.pi / 4):
    focal = height / (2.0 * np.tan(float(fovy) / 2.0))
    return focal, focal, width / 2.0, height / 2.0


def _minmax(values):
    values = np.asarray(values, dtype=np.float64)
    span = float(values.max() - values.min()) if len(values) else 0.0
    if span < 1e-9:
        return np.ones_like(values) * 0.5
    return (values - values.min()) / span


def rank_grasp_candidates(
    gg,
    target_points,
    target_mask,
    depth,
    *,
    max_angle_deg=35.0,
    max_depth_error=0.08,
    min_width=0.005,
    max_width=0.085,
    fovy=np.pi / 4,
):
    """目标约束的多指标排序，返回 [(grasp, composite, diagnostics), ...]。"""
    height, width = target_mask.shape[:2]
    fx, fy, cx, cy = _camera_intrinsics(height, width, fovy=fovy)
    mask_u8 = (target_mask > 0).astype(np.uint8)
    mask_tolerant = cv2.dilate(mask_u8, np.ones((9, 9), np.uint8), iterations=1)
    clearance_map = cv2.distanceTransform(mask_u8, cv2.DIST_L2, 5)
    max_clearance = max(float(clearance_map.max()), 1.0)

    object_center = np.median(target_points, axis=0)
    xy_distances = np.linalg.norm(target_points[:, :2] - object_center[:2], axis=1)
    object_radius = max(float(np.percentile(xy_distances, 90)), 0.015)
    angle_limit = np.deg2rad(max_angle_deg)
    records = []

    for grasp in gg:
        x, y, z = map(float, grasp.translation)
        if not np.isfinite([x, y, z]).all() or z <= 0:
            continue

        u = int(round(fx * x / z + cx))
        v = int(round(fy * y / z + cy))
        if not (0 <= u < width and 0 <= v < height):
            continue

        approach = np.asarray(grasp.rotation_matrix[:, 0], dtype=np.float64)
        angle = float(np.arccos(np.clip(np.dot(approach, [0.0, 0.0, 1.0]), -1.0, 1.0)))
        observed_depth = float(depth[v, u])
        depth_error = abs(z - observed_depth) if np.isfinite(observed_depth) and observed_depth > 0 else np.inf
        width_ok = min_width <= float(grasp.width) <= max_width
        target_ok = bool(mask_tolerant[v, u])

        if angle > angle_limit or not width_ok or not target_ok or depth_error > max_depth_error:
            continue

        center_distance = float(np.linalg.norm(grasp.translation[:2] - object_center[:2]))
        records.append({
            "grasp": grasp,
            "quality": float(grasp.score),
            "center": float(np.exp(-center_distance / object_radius)),
            "clearance": float(clearance_map[v, u] / max_clearance),
            "vertical": float(max(0.0, 1.0 - angle / angle_limit)),
            "depth": float(np.exp(-depth_error / 0.03)),
            "angle_deg": float(np.rad2deg(angle)),
            "depth_error": depth_error,
            "pixel": (u, v),
        })

    if not records:
        raise RuntimeError(
            "没有候选同时满足目标掩码、夹爪宽度、深度一致性和俯视角约束；"
            "请检查目标掩码或相机标定"
        )

    quality_scores = _minmax([item["quality"] for item in records])
    ranked = []
    for item, quality_score in zip(records, quality_scores):
        composite = (
            0.50 * float(quality_score)
            + 0.20 * item["center"]
            + 0.15 * item["clearance"]
            + 0.10 * item["vertical"]
            + 0.05 * item["depth"]
        )
        ranked.append((item["grasp"], composite, item))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def generate_geometric_topdown_grasp(target_points):
    """为简单桌面任务生成基于 PCA 短轴的确定性俯视抓取姿态。"""
    points = np.asarray(target_points, dtype=np.float64)
    if len(points) < 64:
        raise ValueError("几何抓取需要至少 64 个目标点")

    center = np.median(points, axis=0)
    centered_xy = points[:, :2] - center[:2]
    covariance = np.cov(centered_xy, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    closing_xy = eigenvectors[:, int(np.argmin(eigenvalues))]
    closing_xy /= max(np.linalg.norm(closing_xy), 1e-9)

    projected = centered_xy @ closing_xy
    object_width = float(np.percentile(projected, 95) - np.percentile(projected, 5))
    gripper_width = float(np.clip(object_width + 0.012, 0.02, 0.08))

    approach = np.array([0.0, 0.0, 1.0])
    closing = np.array([closing_xy[0], closing_xy[1], 0.0])
    binormal = np.cross(approach, closing)
    rotation = np.column_stack([approach, closing, binormal])

    grasp_array = np.concatenate([
        np.asarray([0.5, gripper_width, 0.02, 0.02]),
        rotation.reshape(-1),
        center,
        np.asarray([-1.0]),
    ]).astype(np.float64)
    return GraspGroup(grasp_array.reshape(1, -1))


# 主函数：GraspNet 生成候选，场景碰撞过滤，目标约束重排。
def run_grasp_inference(
    color_path,
    depth_path,
    sam_mask_path=None,
    *,
    top_k=5,
    visualize=None,
    backend=None,
    fovy=np.pi / 4,
):
    end_points, target_cloud, scene_cloud, target_mask, depth = get_and_process_data(
        color_path, depth_path, sam_mask_path, fovy=fovy
    )
    target_points = np.asarray(target_cloud.points)
    scene_points = np.asarray(scene_cloud.points)
    backend = (backend or os.getenv("GRASP_BACKEND", "hybrid")).strip().lower()
    if backend not in {"hybrid", "graspnet", "geometric"}:
        raise ValueError(f"未知抓取后端: {backend}")

    def predict_with_graspnet():
        from graspnet import pred_decode

        net = get_net()
        with torch.inference_mode():
            predictions = net(end_points)
            decoded = pred_decode(predictions)
        return GraspGroup(decoded[0].detach().cpu().numpy())

    def postprocess(candidates):
        if len(candidates) == 0:
            raise RuntimeError("抓取后端未生成任何候选")
        raw_candidate_count = len(candidates)
        candidates = candidates.nms()
        candidates.sort_by_score()
        detector = ModelFreeCollisionDetector(scene_points, voxel_size=0.008)
        collision_mask, empty_mask = detector.detect(
            candidates,
            approach_dist=0.06,
            collision_thresh=0.01,
            return_empty_grasp=True,
            empty_thresh=0.003,
        )
        candidates = candidates[~(collision_mask | empty_mask)]
        if len(candidates) == 0:
            raise RuntimeError("所有候选均发生碰撞或夹爪内部为空")
        ranked_candidates = rank_grasp_candidates(
            candidates, target_points, target_mask, depth, fovy=fovy
        )
        return raw_candidate_count, len(candidates), ranked_candidates

    selected_backend = backend
    try:
        candidates = (
            generate_geometric_topdown_grasp(target_points)
            if backend == "geometric"
            else predict_with_graspnet()
        )
        raw_count, filtered_count, ranked = postprocess(candidates)
    except RuntimeError as exc:
        if backend != "hybrid":
            raise
        print(f"[WARN] GraspNet 无可靠姿态，自动切换几何俯视抓取: {exc}")
        selected_backend = "geometric-fallback"
        raw_count, filtered_count, ranked = postprocess(
            generate_geometric_topdown_grasp(target_points)
        )

    selected = ranked[:max(1, min(int(top_k), len(ranked)))]
    result = GraspGroup(np.stack([item[0].grasp_array for item in selected], axis=0))

    print(
        f"[INFO] 抓取后端={selected_backend}; 候选: 原始={raw_count}, NMS+碰撞后={filtered_count}, "
        f"目标约束后={len(ranked)}, 返回Top-{len(result)}"
    )
    for index, (grasp, composite, diag) in enumerate(selected[:3], start=1):
        print(
            f"  Top-{index}: 综合={composite:.3f}, 模型={grasp.score:.3f}, "
            f"像素={diag['pixel']}, 俯视角={diag['angle_deg']:.1f}°, "
            f"深度误差={diag['depth_error'] * 1000:.1f}mm, 宽度={grasp.width * 1000:.1f}mm"
        )

    if visualize is None:
        visualize = os.getenv("GRASP_VISUALIZE", "0") == "1"
    if visualize:
        o3d.visualization.draw_geometries([
            scene_cloud,
            *result.to_open3d_geometry_list(),
        ])
    return result

# 工具：通用执行器
def _run_planners(robot, env, planner_array, time_array, action, dt=0.002):
    """
    与原代码完全一致的执行逻辑：
    - 不创建新的 action，沿用并更新传入的 action（保证与原来“先前一步的关节位姿”连续）。
    - 关节/笛卡尔两用。
    """
    total_time = np.sum(time_array)
    time_step_num = round(total_time / dt) + 1
    times = np.linspace(0.0, total_time, time_step_num)
    time_cumsum = np.cumsum(time_array)

    for timei in times:
        for j in range(len(time_cumsum)):
            if timei == 0.0:
                break
            if timei <= time_cumsum[j]:
                planner_interpolate = planner_array[j - 1].interpolate(timei - time_cumsum[j - 1])
                if isinstance(planner_interpolate, np.ndarray):
                    joint = planner_interpolate
                    robot.move_joint(joint)
                else:
                    robot.move_cartesian(planner_interpolate)
                    joint = robot.get_joint()
                action[:6] = joint
                env.step(action)
                break
    return action  # 继续复用

def robust_depth_at_pixel(depth_img, u, v, win=4, depth_scale=1.0):
    """使用像素邻域中位数抑制边缘、孔洞和单像素深度噪声。"""
    h, w = depth_img.shape[:2]
    u0, v0 = int(round(u)), int(round(v))
    u1, u2 = max(0, u0 - win), min(w, u0 + win + 1)
    v1, v2 = max(0, v0 - win), min(h, v0 + win + 1)
    patch = depth_img[v1:v2, u1:u2].astype(np.float32)
    vals = patch[np.isfinite(patch) & (patch > 0)]
    if vals.size == 0:
        raise ValueError(f"像素({u},{v})邻域无有效深度")
    return float(np.median(vals)) * float(depth_scale)


# 兼容旧的内部调用名。
_depth_at_median = robust_depth_at_pixel

def _pixel2base_xyz(u, v, Z_m, K, T_base_cam):
    """
    (u,v,Z_m) → 基座系(x,y,z)，单位米
    K = (fx, fy, cx, cy)
    T_base_cam: 可以是 spatialmath.SE3 或 4x4/3x3 ndarray
    """
    fx, fy, cx, cy = K
    Xc = (u - cx) / fx * Z_m
    Yc = (v - cy) / fy * Z_m
    Zc = Z_m
    p_cam = np.array([Xc, Yc, Zc], dtype=np.float32)

    # 1) SE3 对象：用 R @ p + t
    if isinstance(T_base_cam, sm.SE3):
        p_base = T_base_cam.R @ p_cam + T_base_cam.t
        return float(p_base[0]), float(p_base[1]), float(p_base[2])

    # 2) ndarray：支持 4x4 或 3x3
    T = np.asarray(T_base_cam)
    if T.shape == (4, 4):
        p_h = T @ np.array([Xc, Yc, Zc, 1.0], dtype=np.float32)
        return float(p_h[0]), float(p_h[1]), float(p_h[2])
    elif T.shape == (3, 3):
        p_base = T @ p_cam
        return float(p_base[0]), float(p_base[1]), float(p_base[2])

    raise ValueError(f"T_base_cam 形状不支持: {getattr(T_base_cam, 'shape', type(T_base_cam))}")

# 基础步骤封装
def step1_prepose(robot, env, q0, q1, time1, action, dt=0.002):
    parameter0 = JointParameter(q0, q1)
    velocity_parameter0 = QuinticVelocityParameter(time1)
    trajectory_parameter0 = TrajectoryParameter(parameter0, velocity_parameter0)
    planner1 = TrajectoryPlanner(trajectory_parameter0)
    time_array = [0.0, time1]
    planner_array = [planner1]
    return _run_planners(robot, env, planner_array, time_array, action, dt)


def step2_approach(robot, env, T1, T2, time2, action, dt=0.002):
    position_parameter1 = LinePositionParameter(T1.t, T2.t)
    attitude_parameter1 = OneAttitudeParameter(sm.SO3(T1.R), sm.SO3(T2.R))
    cartesian_parameter1 = CartesianParameter(position_parameter1, attitude_parameter1)
    velocity_parameter1 = QuinticVelocityParameter(time2)
    trajectory_parameter1 = TrajectoryParameter(cartesian_parameter1, velocity_parameter1)
    planner2 = TrajectoryPlanner(trajectory_parameter1)
    time_array = [0.0, time2]
    planner_array = [planner2]
    action = _run_planners(robot, env, planner_array, time_array, action, dt)
    return action


def step3_to_grasp(robot, env, T2, T3, time3, action, dt=0.002):
    position_parameter2 = LinePositionParameter(T2.t, T3.t)
    attitude_parameter2 = OneAttitudeParameter(sm.SO3(T2.R), sm.SO3(T3.R))
    cartesian_parameter2 = CartesianParameter(position_parameter2, attitude_parameter2)
    velocity_parameter2 = QuinticVelocityParameter(time3)
    trajectory_parameter2 = TrajectoryParameter(cartesian_parameter2, velocity_parameter2)
    planner3 = TrajectoryPlanner(trajectory_parameter2)
    time_array = [0.0, time3]
    planner_array = [planner3]
    return _run_planners(robot, env, planner_array, time_array, action, dt)

def move_to_grasp_pose(robot, env,
                       q0, q1, T_wo,
                       time1=1.0, time2=1.0, time3=1.0,
                       action=None, dt=0.002,
                       approach_offset=(-0.1, 0.0, 0.0)):
    if action is None:
        action = np.zeros(7)
    # 1) 预抓取
    action = step1_prepose(robot, env, q0, q1, time1, action, dt)
    # 2) 接近（保持原来 robot.set_joint(q1) 的行为）
    robot.set_joint(q1)
    T1 = robot.get_cartesian()
    T2 = T_wo * sm.SE3(*approach_offset)
    action = step2_approach(robot, env, T1, T2, time2, action, dt)
    # 3) 到抓取位姿
    T3 = T_wo
    action = step3_to_grasp(robot, env, T2, T3, time3, action, dt)
    return action, T2, T3


def close_gripper(env, action, loops=1000, delta=0.2):
    """
    与原逻辑完全一致：仅改 action[-1]，持续复用上一步留下的 action[:6]
    """
    for _ in range(loops):
        action[-1] += delta
        action[-1] = np.min([action[-1], 255])
        env.step(action)
    return action


def move_to_point(robot, env,
                  T_start,               # 抓起后的起点位姿（一般是 T3/T3_meas）
                  target,                # 目标点：支持 (x,y)、(x,y,z) 或 SE3
                  time4=1.0, time5=1.0, time6=1.0,
                  action=None, dt=0.002,
                  lift_height=0.3,       # 第4步：向上抬高
                  descend_dist=0.20,      # 第6步前的最小安全悬停距离
                  keep_orientation=True  # 是否保持 T_start 的朝向
                  ):
    """
    等价原 4~6 步，但把“目标点”参数化：
      - target=(x,y)：释放高度沿用旧逻辑
      - target=(x,y,z)：(x,y,z) 是最终释放位姿，不再先加高后固定下降
      - target=SE3：该位姿是最终释放位姿
    返回: action, (T4, T5, T6)
    """
    if action is None:
        action = np.zeros(7)

    # --- 第4步：抬高 ---
    T4 = sm.SE3.Trans(0.0, 0.0, lift_height) * T_start
    pos4 = LinePositionParameter(T_start.t, T4.t)
    att4 = OneAttitudeParameter(sm.SO3(T_start.R), sm.SO3(T4.R))
    cart4 = CartesianParameter(pos4, att4)
    vel4 = QuinticVelocityParameter(time4)
    traj4 = TrajectoryParameter(cart4, vel4)
    planner4 = TrajectoryPlanner(traj4)

    # --- 计算最终释放位姿（T6）---
    if isinstance(target, sm.SE3):
        T_release = target if not keep_orientation else (
            sm.SE3.Trans(*target.t) * sm.SE3(sm.SO3(T4.R))
        )
    else:
        if len(target) == 2:
            x, y = target
            release_z = T4.t[2] - abs(descend_dist)
            T_release = sm.SE3.Trans(x, y, release_z) * sm.SE3(sm.SO3(T4.R))
        elif len(target) == 3:
            x, y, z = target
            T_release = sm.SE3.Trans(x, y, z) * sm.SE3(sm.SO3(T4.R)) if keep_orientation \
                        else sm.SE3.Trans(x, y, z)
        else:
            raise ValueError("target 需为 (x,y)、(x,y,z) 或 sm.SE3")

    # --- 第5步：先水平移动到释放点上方，再垂直下降 ---
    hover_z = max(float(T4.t[2]), float(T_release.t[2]) + abs(descend_dist))
    T5 = sm.SE3.Trans(T_release.t[0], T_release.t[1], hover_z) * sm.SE3(sm.SO3(T_release.R))
    pos5 = LinePositionParameter(T4.t, T5.t)
    att5 = OneAttitudeParameter(sm.SO3(T4.R), sm.SO3(T5.R))
    cart5 = CartesianParameter(pos5, att5)
    vel5 = QuinticVelocityParameter(time5)
    traj5 = TrajectoryParameter(cart5, vel5)
    planner5 = TrajectoryPlanner(traj5)

    # --- 第6步：到精确释放高度 ---
    T6 = T_release
    pos6 = LinePositionParameter(T5.t, T6.t)
    att6 = OneAttitudeParameter(sm.SO3(T5.R), sm.SO3(T6.R))
    cart6 = CartesianParameter(pos6, att6)
    vel6 = QuinticVelocityParameter(time6)
    traj6 = TrajectoryParameter(cart6, vel6)
    planner6 = TrajectoryPlanner(traj6)

    # 合并执行（与原 step4to6_run 等价）
    action = _run_planners(robot, env,
                           [planner4, planner5, planner6],
                           [0.0, time4, time5, time6],
                           action, dt)

    return action, (T4, T5, T6)

def step4_make_planner(T3, time4):
    T4 = sm.SE3.Trans(0.0, 0.0, 0.3) * T3
    position_parameter3 = LinePositionParameter(T3.t, T4.t)
    attitude_parameter3 = OneAttitudeParameter(sm.SO3(T3.R), sm.SO3(T4.R))
    cartesian_parameter3 = CartesianParameter(position_parameter3, attitude_parameter3)
    velocity_parameter3 = QuinticVelocityParameter(time4)
    trajectory_parameter3 = TrajectoryParameter(cartesian_parameter3, velocity_parameter3)
    planner4 = TrajectoryPlanner(trajectory_parameter3)
    return planner4, T4


def step5_make_planner(T4, time5):
    T5 = sm.SE3.Trans(1.4, 0.3, T4.t[2]) * sm.SE3(sm.SO3(T4.R))
    position_parameter4 = LinePositionParameter(T4.t, T5.t)
    attitude_parameter4 = OneAttitudeParameter(sm.SO3(T4.R), sm.SO3(T5.R))
    cartesian_parameter4 = CartesianParameter(position_parameter4, attitude_parameter4)
    velocity_parameter4 = QuinticVelocityParameter(time5)
    trajectory_parameter4 = TrajectoryParameter(cartesian_parameter4, velocity_parameter4)
    planner5 = TrajectoryPlanner(trajectory_parameter4)
    return planner5, T5


def step6_make_planner(T5, time6):
    T6 = sm.SE3.Trans(0.0, 0.0, -0.25) * T5 # 放置位姿，下降25cm
    position_parameter6 = LinePositionParameter(T5.t, T6.t)
    attitude_parameter6 = OneAttitudeParameter(sm.SO3(T5.R), sm.SO3(T6.R))
    cartesian_parameter6 = CartesianParameter(position_parameter6, attitude_parameter6)
    velocity_parameter6 = QuinticVelocityParameter(time6)
    trajectory_parameter6 = TrajectoryParameter(cartesian_parameter6, velocity_parameter6)
    planner6 = TrajectoryPlanner(trajectory_parameter6)
    return planner6, T6


def open_gripper(env, action, loops=1000, delta=0.2):
    for _ in range(loops):
        action[-1] -= delta
        action[-1] = np.max([action[-1], 0])
        env.step(action)
    return action


def step7_retract(robot, env, T6, time7, action, dt=0.002):
    T7 = sm.SE3.Trans(0.0, 0.0, 0.1) * T6
    position_parameter7 = LinePositionParameter(T6.t, T7.t)
    attitude_parameter7 = OneAttitudeParameter(sm.SO3(T6.R), sm.SO3(T7.R))
    cartesian_parameter7 = CartesianParameter(position_parameter7, attitude_parameter7)
    velocity_parameter7 = QuinticVelocityParameter(time7)
    trajectory_parameter7 = TrajectoryParameter(cartesian_parameter7, velocity_parameter7)
    planner7 = TrajectoryPlanner(trajectory_parameter7)
    time_array = [0.0, time7]
    planner_array = [planner7]
    action = _run_planners(robot, env, planner_array, time_array, action, dt)
    return action, T7


def step8_go_home(robot, env, q8, q9, time8, action, dt=0.002):
    parameter8 = JointParameter(q8, q9)
    velocity_parameter8 = QuinticVelocityParameter(time8)
    trajectory_parameter8 = TrajectoryParameter(parameter8, velocity_parameter8)
    planner8 = TrajectoryPlanner(trajectory_parameter8)
    time_array = [0.0, time8]
    planner_array = [planner8]
    return _run_planners(robot, env, planner_array, time_array, action, dt)

def back_to_zero(robot, env,
                  T6, q_home,
                  time7=1.0, time8=1.0,
                  action=None, dt=0.002):
    """
    第7步：抬起离开（T6 -> T7）
    第8步：回到初始（q8 -> q_home）
    返回：action, T7
    """
    if action is None:
        action = np.zeros(7)

    # 第7步：抬起
    action, T7 = step7_retract(robot, env, T6, time7, action, dt)

    # 读取当前真实关节角，确保回家轨迹连续
    q8 = robot.get_joint()

    # 第8步：回到初始
    action = step8_go_home(robot, env, q8, q_home, time8, action, dt)

    return action, T7

def camera_calibration_from_env(env, image_shape=None, camera_name="cam"):
    """从 MuJoCo 运行时读取 OpenCV 相机外参和内参，避免复制 XML 常量。"""
    import mujoco

    camera_id = mujoco.mj_name2id(
        env.mj_model, mujoco.mjtObj.mjOBJ_CAMERA, camera_name
    )
    if camera_id < 0:
        raise ValueError(f"MuJoCo 场景中不存在相机: {camera_name}")

    # MuJoCo 相机坐标是 x向右/y向上/z向后；点云使用 OpenCV 的
    # x向右/y向下/z向前，因此需要翻转 y、z 轴。
    rotation_mujoco = env.mj_data.cam_xmat[camera_id].reshape(3, 3)
    rotation_cv = rotation_mujoco @ np.diag([1.0, -1.0, -1.0])
    translation = env.mj_data.cam_xpos[camera_id].copy()
    T_world_camera = sm.SE3.Rt(rotation_cv, translation)

    if image_shape is None:
        height, width = env.height, env.width
    else:
        height, width = image_shape[:2]
    fovy = np.deg2rad(float(env.mj_model.cam_fovy[camera_id]))
    intrinsics = _camera_intrinsics(height, width, fovy=fovy)
    return T_world_camera, intrinsics


def prepare_grasp_context(env, gg):
    """
    抓取前的初始化，计算抓取位姿和初始关节角。
    返回:
        robot: 机器人实例
        action: 初始动作数组 (7维)
        q0: 当前关节角
        q1: 预抓取姿态
        T_wo: 物体相对于世界坐标系的抓取位姿
    """
    robot = env.robot
    action = np.zeros(7)

    # 从 MuJoCo 场景读取相机到世界坐标的位姿。
    T_wc, _ = camera_calibration_from_env(env)

    # 计算物体相对于相机的位姿
    T_co = sm.SE3.Trans(gg.translations[0]) * sm.SE3(
        sm.SO3.TwoVectors(x=gg.rotation_matrices[0][:, 0], y=gg.rotation_matrices[0][:, 1])
    )

    # 得到物体相对于世界的位姿
    T_wo = T_wc * T_co

    # 当前关节角
    q0 = robot.get_joint()

    # 预抓取姿态（固定安全位姿）
    q1 = np.array([0.0, 0.0, np.pi/2, 0.0, -np.pi/2, 0.0])

    return robot, action, q0, q1, T_wo, T_wc

class GraspFlow:
    """
    极薄上下文：
    - 保存 env/robot/action/q0/q1/T_wo
    - 记录关键位姿 T1~T7，便于后续步骤衔接
    - 暴露零/少参数方法，内部用你的默认参数保持行为一致
    """
    def __init__(self, env, gg, dt=0.002):
        self.env = env
        self.dt = dt
        # 复用你的初始化函数
        self.robot, self.action, self.q0, self.q1, self.T_wo, self.T_base_cam = prepare_grasp_context(env, gg)
        self._cached_img_size = None 
        # 中间位姿
        self.T1 = self.T2 = self.T3 = self.T4 = self.T5 = self.T6 = self.T7 = None
        self._target_cache = {}

    @classmethod
    def from_env(cls, env, dt=0.002):
        self = object.__new__(cls)
        self.env = env
        self.dt = dt
        self.robot = env.robot
        import numpy as np
        self.action = np.zeros(7)
        self.q0 = self.robot.get_joint()
        self.q1 = np.array([0.0, 0.0, np.pi/2, 0.0, -np.pi/2, 0.0])

        self.T_base_cam, self.K = camera_calibration_from_env(env)

        # 抓取相关位姿先置空
        self.T_wo = None
        self.T1 = self.T2 = self.T3 = self.T4 = self.T5 = self.T6 = self.T7 = None
        return self
    
    def _fetch_rgbd(self):
        """从 env 渲染一帧，用于取得当前彩色/深度和尺寸。"""
        imgs = self.env.render()
        color = imgs['img']    # RGB
        depth = imgs['depth']  # 深度
        return color, depth

    def _intrinsics_from_size(self, h, w, fovy=None):
        """和你上游处理一致：由图像尺寸+fovy推导相机内参 (fx,fy,cx,cy)。"""
        if fovy is None:
            import mujoco
            camera_id = mujoco.mj_name2id(
                self.env.mj_model, mujoco.mjtObj.mjOBJ_CAMERA, self.env.camera_name
            )
            if camera_id >= 0:
                fovy = np.deg2rad(float(self.env.mj_model.cam_fovy[camera_id]))
            else:
                fovy = getattr(self.env, "fovy", np.pi / 4)
        focal = h / (2.0 * np.tan(fovy / 2.0))
        cx = w / 2.0
        cy = h / 2.0
        return (focal, focal, cx, cy)

    # 1~3步：移至抓取位姿（预抓取→接近→到达）
    def move_to_grasp_pose(self, time1=1.0, time2=1.0, time3=1.0, approach_offset=(-0.1, 0.0, 0.0)):
        self.action, self.T2, self.T3 = move_to_grasp_pose(
            self.robot, self.env,
            q0=self.q0, q1=self.q1, T_wo=self.T_wo,
            time1=time1, time2=time2, time3=time3,
            action=self.action, dt=self.dt,
            approach_offset=approach_offset
        )
        return self

    # 关夹爪
    def close_gripper(self, loops=1000, delta=0.2):
        self.action = close_gripper(self.env, self.action, loops=loops, delta=delta)
        return self

    # 4~6步：移动到指定点并下放 —— 仅需传目标点
    def move_to_point(self, target_place,
                      time4=1.0, time5=1.0, time6=1.0,
                      lift_height=0.35,
                      descend_dist=0.20,
                      keep_orientation=True,
                      T_start=None,
                      depth_scale=1.0,   # 若深度是毫米，改为 0.001；仿真通常1.0(米)
                      z_offset=0.08):   # 目标表面到夹爪中心的释放间隙
        # 若未给起点，用当前真实末端位姿
        if T_start is None:
            T_start = self.robot.get_cartesian()

        # ---- 自动识别 target_place 是像素还是基座 ----
        tgt = target_place
        as_pixel = (
            isinstance(tgt, (tuple, list)) and
            len(tgt) == 2 and
            all(isinstance(v, (int, np.integer)) for v in tgt)
        )

        if as_pixel:
            # 1) 取一帧图像，得到图像尺寸
            color, depth = self._fetch_rgbd()
            h, w = depth.shape[:2]
            # 2) 内参（与上游一致）
            if not self._cached_img_size or self._cached_img_size != (h, w):
                self.K = self._intrinsics_from_size(h, w)  # (fx, fy, cx, cy)
                self._cached_img_size = (h, w)
            # 3) 像素→深度→基座
            u, v = int(tgt[0]), int(tgt[1])
            Zm = robust_depth_at_pixel(depth, u, v, win=4, depth_scale=depth_scale)
            xb, yb, zb = _pixel2base_xyz(u, v, Zm, self.K, self.T_base_cam)
            target_xyz = (xb, yb, zb + float(z_offset))
        else:
            # 已是基座输入，仍可使用 z_offset 调整高度
            if isinstance(tgt, (tuple, list)) and len(tgt) == 3:
                x, y, z = tgt
                target_xyz = (x, y, z + float(z_offset))  # ★ 加上传入的 z_offset
            elif isinstance(tgt, (tuple, list)) and len(tgt) == 2:
                # 仅给了 (x, y)，由 move_to_point 保持兼容行为。
                x, y = tgt
                target_xyz = (x, y)
            elif isinstance(tgt, sm.SE3):
                # 若是完整位姿，可以选择是否在位姿上加高
                T_goal = sm.SE3.Trans(0, 0, float(z_offset)) * tgt
                target_xyz = T_goal
            else:
                raise ValueError("target_place 必须为 (x,y)、(x,y,z) 或 sm.SE3")


        # 调用你原来的 move_to_point（不改签名/实现）
        self.action, (self.T4, self.T5, self.T6) = move_to_point(
            self.robot, self.env,
            T_start=T_start,
            target=target_xyz,
            time4=time4, time5=time5, time6=time6,
            action=self.action, dt=self.dt,
            lift_height=lift_height, descend_dist=descend_dist,
            keep_orientation=keep_orientation
        )
        # 下一段起点沿用
        self.T3 = self.T6
        return self


    # 开夹爪
    def open_gripper(self, loops=1000, delta=0.2):
        self.action = open_gripper(self.env, self.action, loops=loops, delta=delta)
        return self

    # 7+8步：抬起离开并回到初始
    def back_to_zero(self, time7=1.0, time8=1.0):
        # 兜底：如果 T6 为空，优先用当前末端姿态；再退而求其次用 T3
        T6_fallback = self.T6
        if T6_fallback is None:
            try:
                T6_fallback = self.robot.get_cartesian()
                print("[WARN] self.T6 为空，使用当前末端位姿作为 T6")
            except Exception:
                if self.T3 is not None:
                    T6_fallback = self.T3
                    print("[WARN] self.T6 为空，使用 T3 作为 T6")
                else:
                    raise RuntimeError("没有可用的 T6/T3，无法执行 back_to_zero()")

        self.action, self.T7 = back_to_zero(
            self.robot, self.env,
            T6=T6_fallback, q_home=self.q0,
            time7=time7, time8=time8,
            action=self.action, dt=self.dt
        )
        return self

def execute_grasp(env, gg,
                  # 指定放置目标：可给 (x,y)，或 (x,y,z)，或 sm.SE3
                  target_place=(1.4, 0.3),
                  # 每段时长（与原默认一致）
                  t1=1.0, t2=1.0, t3=1.0, t4=1.0, t5=1.0, t6=1.0, t7=1.0, t8=1.0,
                  dt=0.002):
    """
    示例流程（按你需求把动作函数串起来）：
      1) 移至抓取位姿（1~3步）
      2) 关闭夹爪
      3) 移动到“指定点”并下放（4~6步，目标可指定）
      4) 打开夹爪
      5) 7、8 步骤不变：抬起离开、回到初始
    """
    robot = env.robot

    # 0) 计算抓取位姿 T_wo（保持你原逻辑）
    n_wc = np.array([0.0, -1.0, 0.0])
    o_wc = np.array([-1.0, 0.0, -0.5])
    t_wc = np.array([0.85, 0.8, 1.6])
    T_wc = sm.SE3.Trans(t_wc) * sm.SE3(sm.SO3.TwoVectors(x=n_wc, y=o_wc))
    T_co = sm.SE3.Trans(gg.translations[0]) * sm.SE3(
        sm.SO3.TwoVectors(x=gg.rotation_matrices[0][:, 0], y=gg.rotation_matrices[0][:, 1])
    )
    T_wo = T_wc * T_co

    # 初始 action / 姿态
    action = np.zeros(7)
    q0 = robot.get_joint()
    q1 = np.array([0.0, 0.0, np.pi / 2, 0.0, -np.pi / 2, 0.0])

    # 1) 移至抓取位姿（1~3步）
    action, T2, T3 = move_to_grasp_pose(
        robot, env, q0, q1, T_wo,
        time1=t1, time2=t2, time3=t3,
        action=action, dt=dt,
        approach_offset=(-0.1, 0.0, 0.0)  # 与原默认一致
    )

    # 2) 关闭夹爪
    action = close_gripper(env, action, loops=1000, delta=0.2)

    # 3) 移动到“指定点”并下放（4~6步）
    action, (T4, T5, T6) = move_to_point(
        robot, env,
        T_start=T3,                # 从抓取位姿出发
        target=target_place,       # 这里可传 (x,y)/(x,y,z)/SE3
        time4=t4, time5=t5, time6=t6,
        action=action, dt=dt,
        lift_height=0.3,           # 与原默认一致
        descend_dist=0.25,          # 与原默认一致
        keep_orientation=True      # 保持末端朝向不变
    )

    # 4) 打开夹爪
    action = open_gripper(env, action, loops=1000, delta=0.2)

    # 5) 第 7、8 步不变：抬起离开 + 回到初始
    action, T7 = back_to_zero(robot, env, T6, q_home=q0, time7=t7, time8=t8, action=action, dt=dt)

    return True
