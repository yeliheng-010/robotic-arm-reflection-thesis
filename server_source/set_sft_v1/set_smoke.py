"""最长输入和最多成功回复真实更新，独立进程校验adapter重载。"""
import argparse
import time
import torch
from smoke import probe
from v100_attention import kernel_probe
from set_common import ROOT, read, save, sha, verify
from set_runtime import setup, optimizer_step


def update(config):
    output = ROOT/'smoke'
    output.mkdir(exist_ok=False)
    model, params, tok, environment = setup(config)
    save(output/'kernel_probe.json', kernel_probe())
    rows = read(ROOT/'train_encoded.json')
    longest = max(range(len(rows)), key=lambda i:max(len(v['input_ids']) for v in rows[i]['variants']))
    largest = max(range(len(rows)), key=lambda i:len(rows[i]['variants']))
    indices = sorted({longest, largest})
    original = {n:p.detach().cpu().clone() for n,p in params.items()}
    optimizer = torch.optim.AdamW(params.values(), lr=config['learning_rate'])
    scaler = torch.amp.GradScaler('cuda', init_scale=config['amp_init_scale'])
    started = time.monotonic()
    result = optimizer_step(model, params, groups=[rows[i] for i in indices], optimizer=optimizer, scaler=scaler)
    changed = sum(not torch.equal(original[n], p.detach().cpu()) for n,p in params.items())
    assert changed > 0
    torch.save(probe(model, read(ROOT/'eval_encoded.json')[0]['variants'][0]), output/'reference_logits.pt')
    model.save_pretrained(output/'adapter', safe_serialization=True)
    tok.save_pretrained(output/'adapter')
    save(output/'update.json', dict(result=result, indices=indices, changed_tensors=changed,
        max_tokens=max(len(v['input_ids']) for i in indices for v in rows[i]['variants']),
        max_successes=max(len(rows[i]['variants']) for i in indices),
        elapsed_s=time.monotonic()-started, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        environment=environment, manifest_sha256=sha(ROOT/'manifest.json')))


def reload(config):
    output = ROOT/'smoke'
    prior = read(output/'update.json')
    assert prior['manifest_sha256'] == sha(ROOT/'manifest.json')
    model, _, _, environment = setup(config, adapter=output/'adapter')
    actual = probe(model, read(ROOT/'eval_encoded.json')[0]['variants'][0])
    expected = torch.load(output/'reference_logits.pt', weights_only=True)
    error = float((expected-actual).abs().max())
    assert error <= 1e-4
    save(output/'passed.json', dict(passed=True, independent_process=True,
        reload_max_logit_error=error, update=prior, environment=environment,
        manifest_sha256=sha(ROOT/'manifest.json')))
    print(dict(passed=True, reload_error=error), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['update','reload'])
    args = parser.parse_args()
    (update if args.mode == 'update' else reload)(verify())
