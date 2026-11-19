"""区分真实项目源码与明确的PyTorch虚拟命名空间。"""
import hashlib
import importlib.metadata
from pathlib import Path
import sys
import numpy as np
from qualified_prompt_checkpoint_v2.common import PROJECT, RUN, save, sha

VIRTUAL_MODULES = {'torch.classes': '_classes.py', 'torch.ops': '_ops.py'}


def loaded_project_sources(manifest, *, modules=None):
    sources, virtual = {}, []
    for name, module in list((sys.modules if modules is None else modules).items()):
        if name in VIRTUAL_MODULES:
            raw = getattr(module, '__file__', None)
            assert raw == VIRTUAL_MODULES[name], (name, raw)
            virtual.append(dict(module=name, raw_file=raw, reason='virtual_namespace_class_attribute'))
            continue
        raw = vars(module).get('__file__') if module is not None else None
        if not raw:
            continue
        path = Path(raw).resolve()
        if not path.is_relative_to(PROJECT) or path.suffix != '.py' or 'site-packages' in path.parts:
            continue
        expected = manifest['identities'].get(str(path))
        assert path.is_file() and expected is not None and sha(path) == expected, str(path)
        sources[str(path)] = expected
    return dict(sources=sources, virtual_modules=sorted(virtual, key=lambda row: row['module']))


def record(generator, values, *, manifest, encoding):
    arrays = {key: value.detach().cpu().contiguous().numpy() for key, value in values.items()}
    with (RUN / 'input_tensors.npz').open('xb') as stream:
        np.savez_compressed(stream, **arrays)
    tensors = {key: dict(shape=list(a.shape), dtype=str(a.dtype),
                        sha256=hashlib.sha256(a.tobytes()).hexdigest()) for key, a in arrays.items()}
    processor = generator.processor
    save(RUN / 'encoding.json', dict(encoding=encoding, identity=generator.identity,
         input_ids=arrays['input_ids'].tolist(), attention_mask=arrays['attention_mask'].tolist(),
         tensors=tensors, npz_sha256=sha(RUN / 'input_tensors.npz')))
    save(RUN / 'templates.json', dict(processor_chat_template=processor.chat_template,
         tokenizer_chat_template=processor.tokenizer.chat_template,
         decoded_input=processor.tokenizer.decode(arrays['input_ids'][0].tolist(), skip_special_tokens=False)))
    from f_response import MAX_INPUT_TOKENS, MAX_TOKENS, SEED
    provenance = loaded_project_sources(manifest)
    save(RUN / 'generation_config.json', dict(model=generator.model.generation_config.to_dict(),
         explicit=dict(max_new_tokens=MAX_TOKENS, do_sample=False, use_cache=True, logits_to_keep=1,
                       pad_token_id=generator.tokenizer.pad_token_id),
         seed=SEED, enable_thinking=False, max_input_tokens=MAX_INPUT_TOKENS,
         environment=generator.environment,
         versions={name: importlib.metadata.version(name) for name in
                   ('torch', 'transformers', 'peft', 'accelerate', 'bitsandbytes', 'numpy', 'Pillow')},
         loaded_project_sources=provenance['sources'], virtual_modules=provenance['virtual_modules']))
