"""仅接受6880已定位且由3.3.7源码解释的编译签名差异。"""
FIELD_COUNT = 626
COMPILED_SIGNATURE = '10107167426275082415'
LOADED_SIGNATURE = '0'


def serialized_identity(saved, loaded):
    if len(saved) != FIELD_COUNT or set(saved) != set(loaded):
        raise ValueError('Model field set differs')
    if saved.get('signature') != COMPILED_SIGNATURE or loaded.get('signature') != LOADED_SIGNATURE:
        raise ValueError('Unexpected compilation signature pair')
    differences = sorted(k for k in saved if saved[k] != loaded[k])
    if differences != ['signature']:
        raise ValueError('Serialized model fields differ: '+str(differences))
    return dict(serialized_fields_matched=FIELD_COUNT-1, original_exact_audit_passed=False,
                signature=dict(saved=saved['signature'], loaded=loaded['signature'],
                               serialized_in_mjb=False), model_mutated=False)
