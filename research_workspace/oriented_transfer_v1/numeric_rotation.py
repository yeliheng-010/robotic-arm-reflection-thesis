"""重放账本最后完整行之后的首个失败端点，不重复全部搜索。"""
from itertools import islice
from unittest.mock import patch
import numeric_probe
import ot_endpoints
from ot_register import RUN

if __name__=='__main__':
    count=sum(1 for _ in (RUN/'probe/capsule_964345/endpoints.jsonl').open())
    original=ot_endpoints.candidates
    def remaining(*args,**kwargs):
        return islice(original(*args,**kwargs),count,None)
    print(dict(first_unwritten_endpoint=count),flush=True)
    with patch.object(ot_endpoints,'candidates',remaining):
        numeric_probe.main()
