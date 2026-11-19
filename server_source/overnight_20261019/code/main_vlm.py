import os


# --- 强制覆盖代理设置 ---
# 无论系统变量是什么，都强制指向 HTTP 协议
os.environ["http_proxy"] = "http://127.0.0.1:7897"
os.environ["https_proxy"] = "http://127.0.0.1:7897"
os.environ["all_proxy"] = "http://127.0.0.1:7897" # httpx 有时会优先读取这个
import sys
import cv2
import json
import mujoco
import matplotlib.pyplot as plt 
import time
import spatialmath as sm
import numpy as np

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, 'graspnet-baseline', 'models'))
sys.path.append(os.path.join(ROOT_DIR, 'graspnet-baseline', 'dataset'))
sys.path.append(os.path.join(ROOT_DIR, 'graspnet-baseline', 'utils'))
sys.path.append(os.path.join(ROOT_DIR, 'manipulator_grasp'))

from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv

from vlm_process import  segment_and_crop_mask,choose_model, process_sam_results, generate_robot_actions, _bbox_center
from grasp_process import (
    run_grasp_inference,
    GraspFlow,
    camera_calibration_from_env,
    robust_depth_at_pixel,
)
from vision_agent import plan_and_ground_robot_actions

# 全局变量
global color_img, depth_img, env
color_img = None
depth_img = None
env = None


#获取彩色和深度图像数据
def get_image(env):
    global color_img, depth_img
     # 从环境渲染获取图像数据
    imgs = env.render()

    # 提取彩色和深度图像数据
    color_img = imgs['img']   # 这是RGB格式的图像数据
    depth_img = imgs['depth'] # 这是深度数据

    # 将RGB图像转换为OpenCV常用的BGR格式
    color_img = cv2.cvtColor(color_img, cv2.COLOR_RGB2BGR)

    return color_img, depth_img

#构造回调函数，不断调用
def callback(color_frame, depth_frame):
    global color_img, depth_img
    scaling_factor_x = 1
    scaling_factor_y = 1

    color_img = cv2.resize(
        color_frame, None,
        fx=scaling_factor_x,
        fy=scaling_factor_y,
        interpolation=cv2.INTER_AREA
    )
    depth_img = cv2.resize(
        depth_frame, None,
        fx=scaling_factor_x,
        fy=scaling_factor_y,
        interpolation=cv2.INTER_NEAREST
    )

    if color_img is not None and depth_img is not None:
        test_grasp()

import json
import time
import numpy as np
import spatialmath as sm


SCENE_BODY_ALIASES = {
    "duck": "Duck",
    "yellow duck": "Duck",
    "rubik": "rubik",
    "rubiks cube": "rubik",
    "rubik's cube": "rubik",
    "cube": "rubik",
    "apple": "Apple",
    "banana": "Banana",
    "hammer": "Hammer",
    "knife": "Knife",
    "flashlight": "Flashlight",
    "red block": "RedBlock",
    "red cube": "RedBlock",
    "红色方块": "RedBlock",
    "green cylinder": "GreenCylinder",
    "绿色圆柱": "GreenCylinder",
    "purple capsule": "PurpleCapsule",
    "紫色胶囊": "PurpleCapsule",
    "orange sphere": "OrangeSphere",
    "orange ball": "OrangeSphere",
    "橙色小球": "OrangeSphere",
    "blue bin": "BlueBin",
    "blue container": "BlueBin",
    "蓝色箱子": "BlueBin",
    "red bin": "RedBin",
    "red container": "RedBin",
    "红色箱子": "RedBin",
    "sorting tray": "SortingTray",
    "yellow tray": "SortingTray",
    "tray": "SortingTray",
    "托盘": "SortingTray",
    "safety divider": "SafetyDivider",
    "divider": "SafetyDivider",
    "隔板": "SafetyDivider",
}


def _normalize_object_name(value):
    return " ".join(
        str(value).lower().replace("_", " ").replace("'", "").split()
    )


def _resolve_scene_body_id(env, object_name):
    """把 VLM 的开放词汇名称映射到 MuJoCo 根物体 body。"""
    normalized = _normalize_object_name(object_name)
    alias_key = normalized.replace("’", "")
    expected = SCENE_BODY_ALIASES.get(alias_key)
    if expected:
        body_id = mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, expected)
        if body_id >= 0:
            return body_id

    for body_id in range(env.mj_model.nbody):
        body_name = mujoco.mj_id2name(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        if not body_name:
            continue
        candidate = _normalize_object_name(body_name)
        if candidate in normalized or normalized in candidate:
            return body_id
    return -1


def execute_actions_from_res(res, color_img, depth_img, env):
    """
    根据 res["action_json_str"] 依次将动作派发到 flow
    
    ★ 关键改进：在任何机械臂运动前，预先计算所有像素坐标
    """
    if color_img is None or depth_img is None:
        print("[WARNING] Waiting for image data...")
        return

    # 步骤1: 解析动作序列
    action_data = res.get("action_json_str", None)
    if action_data is None:
        raise ValueError("res['action_json_str'] 不存在")

    if isinstance(action_data, str):
        action_data = json.loads(action_data)

    if isinstance(action_data, dict) and "action_components" in action_data:
        actions = action_data["action_components"]
    elif isinstance(action_data, list):
        actions = action_data
    else:
        raise ValueError("action_json_str 的结构不正确")

    def _fmt(obj):
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return str(obj)

    print("\n========== 执行动作清单 ==========")
    for idx, item in enumerate(actions):
        print(f"[计划] #{idx}: action={item.get('action')}  "
              f"component={_fmt(item.get('component'))}  "
              f"description={item.get('description')}")
    print("================================\n")

    #  步骤2: 预计算所有像素坐标 
    print("\n" + "="*60)
    print("📸 预计算阶段：在机械臂移动前计算所有目标坐标")
    print("="*60)
    
    # 2.1 提取所有需要坐标的像素点
    pixel_list = []
    action_pixel_map = {}  # {动作索引: 像素坐标}
    
    for idx, item in enumerate(actions):
        args = item.get("args", {}) or {}
        pixel = args.get("pixel", None)
        
        if pixel is not None:
            if not (isinstance(pixel, (list, tuple)) and len(pixel) == 2):
                print(f"[WARN] 动作 #{idx} 的 pixel 格式不正确: {pixel}")
                continue
            
            u, v = int(pixel[0]), int(pixel[1])
            pixel_tuple = (u, v)
            
            # 去重记录
            if pixel_tuple not in pixel_list:
                pixel_list.append(pixel_tuple)
            
            action_pixel_map[idx] = pixel_tuple
    
    print(f"[INFO] 检测到 {len(pixel_list)} 个需要坐标转换的像素点: {pixel_list}")
    
    # 2.2/2.3 从 MuJoCo 当前相机读取外参与内参，避免场景修改后漂移。
    h, w = depth_img.shape[:2]
    T_base_cam, K = camera_calibration_from_env(env, depth_img.shape)
    
    print(f"[INFO] 图像尺寸: {w}x{h}")
    print(f"[INFO] 相机内参: fx={K[0]:.2f}, fy={K[1]:.2f}, cx={K[2]:.2f}, cy={K[3]:.2f}")
    
    # 2.4 批量计算坐标（此时机械臂还未移动，场景无遮挡）
    coord_cache = {}
    
    for u, v in pixel_list:
        # 检查边界
        if not (0 <= u < w and 0 <= v < h):
            print(f"[WARN] 像素 ({u},{v}) 超出图像范围，跳过")
            continue
        
        # 使用邻域中位数，避免单像素落到背景/深度孔洞。
        Zm = robust_depth_at_pixel(depth_img, u, v, win=4)
        
        if Zm <= 0 or not np.isfinite(Zm):
            print(f"[WARN] 像素 ({u},{v}) 深度无效: {Zm}")
            continue
        
        # 像素→基座坐标转换
        xb, yb, zb = _pixel2base_xyz(u, v, Zm, K, T_base_cam)
        coord_cache[(u, v)] = (xb, yb, zb)
        
        print(f"  [✓] 像素 ({u:3d},{v:3d}) → 深度 {Zm:.4f}m → "
              f"基座 ({xb:.4f}, {yb:.4f}, {zb:.4f})")
    
    print(f"[INFO] 成功预计算 {len(coord_cache)} 个坐标")
    print("="*60 + "\n")
    
    if len(coord_cache) == 0 and len(pixel_list) > 0:
        raise RuntimeError("所有像素点的坐标转换都失败了！")

    # 步骤3: 执行动作序列（使用预计算的坐标）
    flow = None
    gg = None
    masks = None
    report = {
        "picked_object": None,
        "grasp_displacement_m": None,
        "placement_xy_error_m": None,
        "success": None,
    }
    picked_body_id = -1
    picked_initial_position = None
    latest_place_target = None

    for i, item in enumerate(actions):
        action = item.get("action")
        args = item.get("args", {}) or {}
        pixel = args.get("pixel", None)

        # 统一把 pixel 转成 tuple
        if pixel is not None:
            if not (isinstance(pixel, (list, tuple)) and len(pixel) == 2):
                raise ValueError(f"第 {i} 个动作的 pixel 格式不正确: {pixel}")
            point_xy = (int(pixel[0]), int(pixel[1]))
        else:
            point_xy = None

        t0 = time.time()
        print(f"\n--- 执行动作 #{i} | {action} ---")
        if point_xy is not None:
            print(f"[输入参数] pixel={point_xy}")
        if args and (pixel is None or len(args) > 1):
            rest_args = {k: v for k, v in args.items() if k != "pixel"}
            if rest_args:
                print(f"[输入参数] 其他 args={_fmt(rest_args)}")

        # ========== move_to_grasp_pose ==========
        if action == "move_to_grasp_pose":
            if point_xy is None:
                raise ValueError(f"第 {i} 个动作 move_to_grasp_pose 缺少 pixel")

            save_path = "mask_final.png"
            print(f"[步骤] 生成目标 mask -> 保存={save_path}")
            masks = segment_and_crop_mask(
                image_bgr=color_img,
                point_xy=point_xy,
                radius_px=None,
                depth=depth_img,
                save_path=save_path
            )
            print("[步骤] 运行抓取推理 run_grasp_inference(...)")
            camera_id = mujoco.mj_name2id(
                env.mj_model, mujoco.mjtObj.mjOBJ_CAMERA, env.camera_name
            )
            grasp_fovy = np.deg2rad(float(env.mj_model.cam_fovy[camera_id]))
            gg = run_grasp_inference(
                color_img, depth_img, masks, fovy=grasp_fovy
            )

            component = item.get("component") or []
            object_name = component[0] if component else ""
            picked_body_id = _resolve_scene_body_id(env, object_name)
            if picked_body_id >= 0:
                picked_initial_position = env.mj_data.xpos[picked_body_id].copy()
                report["picked_object"] = mujoco.mj_id2name(
                    env.mj_model, mujoco.mjtObj.mjOBJ_BODY, picked_body_id
                )

            try:
                print(f"[信息] 抓取候选数量: {len(gg)}")
            except Exception:
                print("[信息] 抓取候选数量: <未知类型，无法统计>")

            if flow is None:
                flow = GraspFlow(env, gg)
                print("[状态] 初始化 GraspFlow 完成")

            flow.move_to_grasp_pose()
            print("[结果] move_to_grasp_pose 完成")

        # ========== move_to_point ==========
        elif action == "move_to_point":
            if point_xy is None:
                raise ValueError(f"第 {i} 个动作 move_to_point 缺少 pixel")
                # 若还没有 flow（例如序列一上来就是 move_to_point），这里临时初始化
            if flow is None:
                flow = GraspFlow.from_env(env)
                print("[状态] 初始化 GraspFlow（无抓取）完成")
            
            # 使用预计算的基座坐标（避免遮挡）
            if point_xy in coord_cache:
                target_base_coord = coord_cache[point_xy]
                latest_place_target = np.asarray(target_base_coord, dtype=np.float64)
                print(f"[步骤] 使用预计算的基座坐标: {target_base_coord}")
                print(f"       (原像素坐标: {point_xy})")
                
                # 传入基座坐标（3元组），而不是像素坐标
                release_clearance = float(args.get("z_offset_m", 0.08))
                flow.move_to_point(target_base_coord, z_offset=release_clearance)
                if picked_body_id >= 0 and picked_initial_position is not None:
                    current_position = env.mj_data.xpos[picked_body_id].copy()
                    displacement = float(np.linalg.norm(current_position - picked_initial_position))
                    report["grasp_displacement_m"] = displacement
                    print(f"[验证] 被抓物体累计位移: {displacement:.3f}m")
                print("[结果] move_to_point 完成（已到达目标位置）")
            else:
                print(f"[ERROR] 像素 {point_xy} 的坐标未在预计算中找到！")
                raise RuntimeError(f"缺少坐标缓存: {point_xy}")

        # ========== close_gripper ==========
        elif action == "close_gripper":
            print("[步骤] 关闭夹爪")
            flow.close_gripper()
            print("[结果] close_gripper 完成")

        # ========== open_gripper ==========
        elif action == "open_gripper":
            print("[步骤] 打开夹爪")
            flow.open_gripper()
            # 释放后让物体短暂稳定，再以真实 MuJoCo 位姿评价任务结果。
            for _ in range(250):
                env.step(flow.action)
            if picked_body_id >= 0 and latest_place_target is not None:
                final_position = env.mj_data.xpos[picked_body_id].copy()
                xy_error = float(np.linalg.norm(final_position[:2] - latest_place_target[:2]))
                report["placement_xy_error_m"] = xy_error
                moved = (report["grasp_displacement_m"] or 0.0) >= 0.05
                report["success"] = bool(moved and xy_error <= 0.12)
                print(
                    f"[验证] 最终物体位置={np.round(final_position, 4).tolist()}, "
                    f"目标XY误差={xy_error:.3f}m, success={report['success']}"
                )
            print("[结果] open_gripper 完成")

        # ========== back_to_zero ==========
        elif action == "back_to_zero":
            print("[步骤] 回到初始位姿")
            flow.back_to_zero()
            print("[结果] back_to_zero 完成")

        else:
            print(f"[WARN] 未知动作 '{action}'，跳过。")

        dt = time.time() - t0
        print(f"[耗时] {dt:.3f}s  —— #{i} {action}")

    print("\n=== 全部动作执行完成 ===\n")
    print("[任务评估]", json.dumps(report, ensure_ascii=False))
    return report


# 辅助函数：像素→基座坐标转换（需要在文件开头定义）
def _pixel2base_xyz(u, v, Z_m, K, T_base_cam):
    """
    (u,v,Z_m) → 基座系(x,y,z)，单位米
    K = (fx, fy, cx, cy)
    T_base_cam: spatialmath.SE3 或 4x4/3x3 ndarray
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

def test_grasp():
    global color_img, depth_img, env

    if color_img is None or depth_img is None:
        print("[WARNING] Waiting for image data...")
        return

    # 用户输入指令 
    instruction = input("请输入操作指令（例如：将小黄鸭放在魔方上面）: ").strip()
    if not instruction:
        print("[提示] 未输入指令，默认执行：将小黄鸭放在魔方上面")
        instruction = "将小黄鸭放在魔方上面"

    # 调用多模态规划
    res = plan_and_ground_robot_actions(
        instruction=instruction,
        image_path=color_img,
        save_vis_prefix="logs/run1"
    )

    print(f"【用户指令】{instruction}")
    print("【规划输出】", res["action_json_str"])

    # 执行动作序列
    execute_actions_from_res(res, color_img, depth_img, env)


if __name__ == '__main__':
    env = UR5GraspEnv()
    try:
        env.reset()
        while True:
            for _ in range(500):
                env.step()
            color_img, depth_img = get_image(env)
            callback(color_img, depth_img)
    except KeyboardInterrupt:
        print("\n[INFO] 用户终止，正在关闭 MuJoCo 环境")
    finally:
        env.close()
