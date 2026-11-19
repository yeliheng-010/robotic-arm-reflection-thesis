"""从基础权重独立开始，完整一轮20次更新，不使用smoke权重。"""
import json
import os
import time
import traceback
import torch
from stability.sft_data import epoch_groups
from data import ROOT,read,save,sha
from runtime import verify_manifest,setup,optimizer_step
from smoke import probe


def checkpoint(model,tok,*,output,step,optimizer,scaler):
    directory = output/f'checkpoint_{step:03d}'
    model.save_pretrained(directory,safe_serialization=True)
    tok.save_pretrained(directory)
    torch.save(dict(optimizer=optimizer.state_dict(),scaler=scaler.state_dict(),
                    torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),
                    step=step),directory/'training_state.pt')


def train_epoch(model,params,tok,*,config,output):
    rows = read(ROOT/'train_encoded.json')
    order = epoch_groups(len(rows),accumulation=config['accumulation'],seed=config['seed'])
    assert len(order)==20 and len(order[-1])==7
    save(output/'epoch_order.json',order)
    optimizer = torch.optim.AdamW(params.values(),lr=config['learning_rate'])
    scaler = torch.amp.GradScaler('cuda',init_scale=config['amp_init_scale'])
    updates,started = [],time.monotonic()
    for step,indices in enumerate(order,1):
        update = optimizer_step(model,params,rows=[rows[i] for i in indices],
                                optimizer=optimizer,scaler=scaler)
        update.update(step=step,total_steps=len(order),indices=indices,
                      elapsed_s=time.monotonic()-started,peak_allocated_bytes=torch.cuda.max_memory_allocated())
        updates.append(update)
        save(output/'updates.json',updates)
        save(output/'progress.json',dict(phase='training',last_update=update))
        print(json.dumps(update),flush=True)
        if step%5==0 or step==len(order):
            checkpoint(model,tok,output=output,step=step,optimizer=optimizer,scaler=scaler)
    assert sorted(i for u in updates for i in u['indices'])==list(range(159))
    return updates


def main():
    config = verify_manifest()
    smoke = read(ROOT/'smoke/passed.json')
    assert smoke['passed'] and smoke['manifest_sha256']==sha(ROOT/'manifest.json')
    output = ROOT/'training'
    output.mkdir(exist_ok=False)
    save(output/'progress.json',dict(phase='loading',job=os.environ['SLURM_JOB_ID']))
    try:
        model,params,tok,environment = setup(config)
        original = {n:p.detach().cpu().clone() for n,p in params.items()}
        updates = train_epoch(model,params,tok,config=config,output=output)
        changed = sum(not torch.equal(original[n],p.detach().cpu()) for n,p in params.items())
        assert changed>0
        model.save_pretrained(output/'adapter',safe_serialization=True)
        tok.save_pretrained(output/'adapter')
        torch.save(probe(model,read(ROOT/'dev_encoded.json')[0]),output/'reference_logits.pt')
        result = dict(status='completed',environment=environment,updates=len(updates),samples_seen=159,
                      changed_tensors=changed,manifest_sha256=sha(ROOT/'manifest.json'),
                      adapter_files={p.name:sha(p) for p in (output/'adapter').iterdir() if p.is_file()},
                      peak_allocated_bytes=torch.cuda.max_memory_allocated(),test_used=False)
        save(output/'result.json',result)
        save(output/'progress.json',dict(phase='completed',result=result))
        print(json.dumps(result),flush=True)
    except BaseException as error:
        save(output/'failure.json',dict(error=repr(error),traceback=traceback.format_exc()))
        raise


if __name__=='__main__':
    main()
