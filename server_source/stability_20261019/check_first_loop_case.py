import json
from stability.loop_freeze import ROOT,verify
from stability.loop_audit import validate_records,validate_model,read
from stability.collection_worker import verify_pair
from stability.loop_protocol import ARMS
config=verify()
case=0
directory=ROOT/'tasks'/f'{case:02d}'
results={arm:read(directory/arm/'result.json') for arm in ARMS}
for arm,result in results.items():
 validate_records(result,config['tasks'][case])
 verify_pair(result,results['retry'])
 if arm in ('base','adapted'):
  validate_model(directory/arm,result,arm)
print(json.dumps({'case':case,'first_completed_case_audit_passed':True}))
