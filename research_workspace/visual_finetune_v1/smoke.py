"""最长训练样本一次更新，再用独立进程验证保存重载。"""
import argparse
import torch
from vf_common import ROOT, runtime, config, rows, processor, encoded, read, save, sha
from vt_objective import suffix_logits, move
from vf_update import update


def probe(model, values):
    model.eval()
    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
        logits, _ = suffix_logits(model, move(values))
        return logits[0, -1].float().cpu()


def smoke_update(settings):
    output = ROOT/'smoke'
    output.mkdir(exist_ok=False)
    row = next(r for r in rows(settings) if r['input_id'] == settings['longest_train_input'])
    proc = processor(settings)
    values = encoded(row, proc)
    model, params, _, environment = runtime.setup(settings)
    before = {n: p.detach().cpu().clone() for n, p in params.items()}
    optimizer = torch.optim.AdamW(params.values(), lr=settings['learning_rate'])
    scaler = torch.amp.GradScaler('cuda', init_scale=settings['amp_init_scale'])
    result = update(model, params, rows=[values], optimizer=optimizer, scaler=scaler)
    changed = sum(not torch.equal(before[n], p.detach().cpu()) for n, p in params.items())
    assert changed > 0
    model.save_pretrained(output/'adapter', safe_serialization=True)
    proc.save_pretrained(output/'processor')
    torch.save(probe(model, values), output/'reference_logits.pt')
    files = [*list((output/'adapter').glob('*')), output/'reference_logits.pt']
    save(output/'update.json', dict(update=result, changed_tensors=changed, environment=environment,
        input_id=row['input_id'], manifest_sha256=sha(ROOT/'manifest.json'),
        identities={str(p): sha(p) for p in files if p.is_file()},
        peak_allocated_bytes=torch.cuda.max_memory_allocated()))
    print(dict(smoke_updated=True, update=result, changed=changed), flush=True)


def smoke_reload(settings):
    from vf_common import verify
    output = ROOT/'smoke'
    prior = verify(output/'update.json')
    assert prior['manifest_sha256'] == sha(ROOT/'manifest.json')
    row = next(r for r in rows(settings) if r['input_id'] == prior['input_id'])
    values = encoded(row, processor(settings))
    model, _, _, environment = runtime.setup(settings, adapter=output/'adapter')
    actual = probe(model, values)
    expected = torch.load(output/'reference_logits.pt', weights_only=True)
    error = float((expected-actual).abs().max())
    assert error <= 1e-4, f'Reload logits mismatch: {error}'
    save(output/'passed.json', dict(passed=True, reload_max_logit_error=error,
        independent_process=True, environment=environment, manifest_sha256=sha(ROOT/'manifest.json'),
        identities={str(output/'update.json'): sha(output/'update.json')}))
    print(dict(smoke_reloaded=True, max_logit_error=error), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['update', 'reload'])
    mode = parser.parse_args().mode
    (smoke_update if mode == 'update' else smoke_reload)(config())
