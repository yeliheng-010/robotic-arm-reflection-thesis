"""中断或损坏证据只做字节保全复核，不推断已完成动力学。"""
from qualified_closure_mjb_v1.protocol import read, sha, require


def snapshot(folder):
    return {p.name: sha(p) for p in sorted(folder.iterdir())
            if p.is_file() and not p.name.startswith('audit_')}


def needs_partial(folder):
    if (folder/'failure.json').exists() or not (folder/'primary_inventory.json').exists():
        return True
    try:
        result = read(folder/'result.json')
    except (OSError, ValueError):
        return True
    return result.get('error') is not None or result.get('uncertain_step') is not None


def inspect_evidence(folder):
    before = snapshot(folder)
    records, errors = {}, {}
    for name in ('result.json', 'failure.json'):
        if name not in before:
            continue
        try:
            records[name] = read(folder/name)
        except (OSError, ValueError) as error:
            errors[name] = type(error).__name__+': '+str(error)
    unconfirmed = [name for name in before if name.startswith('intent_') and
                   (name.replace('intent_', 'observed_') not in before or
                    name.replace('intent_', 'state_').replace('.json', '.npz') not in before)]
    require(snapshot(folder) == before, 'Partial evidence changed during inspection')
    return dict(scope='failure_evidence_only', trajectory_complete=False, dynamics_validated=False,
                native_execution_certified=False, evidence_hashes=before, original_records=records,
                json_errors=errors, unconfirmed_intents=unconfirmed, integration_replayed=False)
