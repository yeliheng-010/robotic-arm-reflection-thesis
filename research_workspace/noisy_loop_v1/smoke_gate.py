"""冒烟完成后审计全部12项；成功率不作为扩大分母的门槛。"""
import json
from noisyloop.design import ROOT
from noisyloop.run import gate
from stability.collection_status import atomic
from verify import main

gate()
main()
value=json.loads((ROOT/'verification.json').read_text())
assert value['completed']==12 and value['passed']
assert value['exposure']['changed_visible_fields']>0
assert not any(r['invalid'] or r['service_errors'] for r in value['rows'])
atomic(ROOT/'smoke_gate.json',dict(status='ready',tasks=12,
    exposure=value['exposure'],training_approved=0,success_rate_used_as_gate=False))
print('SMOKE_GATE_READY')
