"""完整训练状态与adapter绑定，校验后才能恢复。"""
import json
import random
import torch
from peft import get_peft_model_state_dict, set_peft_model_state_dict
from stability.collection_status import atomic
from stability.sft_freeze import file_hash


def save_bundle(context, path, meta):
    path.mkdir(exist_ok=False)
    model = context['model']
    model.save_pretrained(path/'adapter', safe_serialization=True)
    state = dict(adapter=get_peft_model_state_dict(model),
        optimizer=context['optimizer'].state_dict(), scaler=context['scaler'].state_dict(),
        python_rng=random.getstate(), torch_rng=torch.get_rng_state(),
        cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None,
        meta=meta)
    torch.save(state, path/'training_state.pt')
    files = {str(p.relative_to(path)): file_hash(p) for p in path.rglob('*') if p.is_file()}
    atomic(path/'complete.json', dict(identity=meta['identity'], files=files))


def restore_bundle(context, path, identity):
    complete = json.loads((path/'complete.json').read_text())
    assert complete['identity'] == identity, 'Checkpoint manifest identity changed'
    for name, expected in complete['files'].items():
        assert file_hash(path/name) == expected, 'Checkpoint file corrupted: '+name
    state = torch.load(path/'training_state.pt', map_location='cpu', weights_only=False)
    assert state['meta']['identity'] == identity
    set_peft_model_state_dict(context['model'], state['adapter'])
    context['optimizer'].load_state_dict(state['optimizer'])
    context['scaler'].load_state_dict(state['scaler'])
    random.setstate(state['python_rng'])
    torch.set_rng_state(state['torch_rng'])
    if state['cuda_rng'] is not None:
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    return state['meta']
