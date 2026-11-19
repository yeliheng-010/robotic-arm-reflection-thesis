"""最长输入一次更新，独立进程重载，验证实际模型输出。"""
import argparse
import gc
import time
import torch
from data import ROOT,read,save,sha
from runtime import verify_manifest,setup,optimizer_step
from loss import suffix_loss


def probe(model,row):
    model.eval()
    inputs = {k:torch.tensor([row[k]],device='cuda') for k in ('input_ids','attention_mask')}
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
        return model(**inputs,logits_to_keep=1).logits[0,-1].float().cpu()


def smoke_update(config):
    output = ROOT/'smoke'
    output.mkdir(exist_ok=False)
    model,params,tok,environment = setup(config)
    train = read(ROOT/'train_encoded.json')
    row = max(train,key=lambda r:len(r['input_ids']))
    original = {n:p.detach().cpu().clone() for n,p in params.items()}
    optimizer = torch.optim.AdamW(params.values(),lr=config['learning_rate'])
    scaler = torch.amp.GradScaler('cuda',init_scale=config['amp_init_scale'])
    started = time.monotonic()
    update = optimizer_step(model,params,rows=[row],optimizer=optimizer,scaler=scaler)
    changed = sum(not torch.equal(original[n],p.detach().cpu()) for n,p in params.items())
    assert changed>0
    torch.save(probe(model,read(ROOT/'dev_encoded.json')[0]),output/'reference_logits.pt')
    model.save_pretrained(output/'adapter',safe_serialization=True)
    tok.save_pretrained(output/'adapter')
    save(output/'update.json',dict(update=update,changed_tensors=changed,
        sequence_length=len(row['input_ids']),elapsed_s=time.monotonic()-started,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),environment=environment,
        manifest_sha256=sha(ROOT/'manifest.json')))


def smoke_reload(config):
    output = ROOT/'smoke'
    prior = read(output/'update.json')
    assert prior['manifest_sha256']==sha(ROOT/'manifest.json')
    model,_,_,environment = setup(config,adapter=output/'adapter')
    actual = probe(model,read(ROOT/'dev_encoded.json')[0])
    expected = torch.load(output/'reference_logits.pt',weights_only=True)
    error = float((expected-actual).abs().max())
    assert error<=1e-4, f'Reload logits differ: {error}'
    save(output/'passed.json',dict(passed=True,reload_max_logit_error=error,
        independent_process=True,environment=environment,manifest_sha256=sha(ROOT/'manifest.json'),
        update=prior))
    print('SMOKE_PASSED '+str(error),flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['update','reload'])
    mode = parser.parse_args().mode
    config = verify_manifest()
    (smoke_update if mode=='update' else smoke_reload)(config)
