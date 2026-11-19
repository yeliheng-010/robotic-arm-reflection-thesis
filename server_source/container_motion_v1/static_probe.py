"""冻结前仅用旧开发快照做运动学检查，不执行物理或使用新种子结果。"""
from types import SimpleNamespace
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import mujoco
import numpy as np
import spatialmath as sm
import grasp_process as grasp
import stability.prepose as prepose
from stability.kinematics import set_robot_config
from manipulator_grasp.arm.robot import UR5e
from cl_geometry import compiled
from cl_design import configuration
from cm_common import ROOT, DIAGNOSTIC, LAYOUT, read, save
from cm_planning import choose
from cm_pose import eligible


def flow_for(case, plan):
    item = case['source']['item']
    model,data = compiled(configuration(item,plan['layouts'][str(item['seed'])]))
    record = read(case['rule_final']['result_path'])['records'][0]
    data.qpos[:] = record['candidate_trace']['initial_qpos']
    mujoco.mj_forward(model,data)
    names = ['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
    env = SimpleNamespace(mj_model=model,mj_data=data,joint_names=names,height=480,width=640)
    robot = UR5e()
    robot.set_base(data.body('ur5e_base').xpos)
    robot.set_tool(sm.SE3.Trans(0,0,.13)*sm.SE3.RPY(-np.pi/2,-np.pi/2,0))
    robot.set_joint(np.zeros(6))
    parameters = case['rule_action']['state']['parameters']
    rows = record['candidate_trace']['returned']
    row = np.array(rows[min(parameters['candidate_index'],len(rows)-1)])
    camera,_ = grasp.camera_calibration_from_env(env)
    nominal = camera*sm.SE3.Rt(sm.SO3(row[4:13].reshape(3,3)),row[13:16])
    nominal = sm.SE3.Trans(*parameters['grasp_offset'])*nominal
    return SimpleNamespace(env=env,robot=robot,q0=np.zeros(6),q1=np.array([0,0,np.pi/2,0,-np.pi/2,0]),T_wo=nominal)


def main():
    manifest = read(DIAGNOSTIC/'manifest.json')
    plan = read(LAYOUT/'plan.json')
    rows = []
    hooks = (grasp.move_to_grasp_pose,grasp.move_to_point,prepose.select_prepose)
    with patch.object(UR5e,'set_robot_config',set_robot_config):
        for case in manifest['cases']:
            if not eligible(case['snapshot']['feedback']):
                continue
            flow = flow_for(case,plan)
            result = choose(flow,hooks,parameters=case['rule_action']['state']['parameters'],item=case['source']['item'])
            rows.append(dict(id=case['id'],result=result))
            print(case['id'],[(r['id'],r['feasible'],r['phase']) for r in result['candidates']],flush=True)
    save(ROOT/'STATIC_PROBE.json',dict(physical_executions=0,rows=rows))


if __name__=='__main__':
    main()
