import os
from pathlib import Path
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
from sd_scene import compiled
from f_common import save, sha

ROOT = Path(__file__).resolve().parent
TARGETS = ('RedBlock', 'PurpleCapsule')


def selected(model, index):
    name = model.geom(index).name or ''
    body = model.body(int(model.geom_bodyid[index])).name or ''
    return body in TARGETS or any(s in (name+' '+body).lower() for s in ('finger', 'pad', 'gripper'))


def geometry(model, index):
    body_id = int(model.geom_bodyid[index])
    return dict(id=index, name=model.geom(index).name, body=model.body(body_id).name,
        friction=model.geom_friction[index].tolist(), priority=int(model.geom_priority[index]),
        solmix=float(model.geom_solmix[index]), condim=int(model.geom_condim[index]),
        contype=int(model.geom_contype[index]), conaffinity=int(model.geom_conaffinity[index]),
        body_mass=float(model.body_mass[body_id]), size=model.geom_size[index].tolist())


def main():
    assert os.environ.get('SLURM_JOB_ID')
    model, _ = compiled()
    rows = [geometry(model, i) for i in range(model.ngeom) if selected(model, i)]
    pairs = [dict(id=i, geom1=model.geom(int(model.pair_geom1[i])).name,
        geom2=model.geom(int(model.pair_geom2[i])).name, friction=model.pair_friction[i].tolist(),
        dim=int(model.pair_dim[i])) for i in range(model.npair)]
    actuators = [dict(name=model.actuator(i).name, ctrlrange=model.actuator_ctrlrange[i].tolist(),
        forcerange=model.actuator_forcerange[i].tolist(),
        force_limited=bool(model.actuator_forcelimited[i])) for i in range(model.nu)]
    result = dict(geoms=rows, explicit_pairs=pairs, actuators=actuators,
        dynamics_steps=0, physical_attempts=0, model_calls=0, training_updates=0,
        identities={str(Path(__file__)): sha(__file__)},
        limitation='Compiled settings only; no measured contact material, grasp capacity or recovery')
    save(ROOT/'results'/('job_'+os.environ['SLURM_JOB_ID']+'.json'), result)
    print(dict(geoms=rows, explicit_pairs=pairs, dynamics_steps=0), flush=True)


if __name__ == '__main__':
    main()
