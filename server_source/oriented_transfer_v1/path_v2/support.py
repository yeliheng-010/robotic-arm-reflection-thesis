"""原支撑接触只能在竖直抬升时单调退出，脱离后不可恢复。"""
from guard_policy import SUPPORTS

NUMERIC_DISTANCE_M=1e-9


def key(row):
    return tuple(sorted(row['geoms'])),tuple(sorted(row['roots']))


def depths(rows):
    result={}
    for row in rows:
        if any(r.startswith(SUPPORTS) for r in row['roots']):
            name=key(row)
            result[name]=min(result.get(name,0.),row['distance'])
    return result


class Guard:
    def __init__(self, baseline):
        self.previous=depths(baseline)
        self.active=bool(self.previous)

    def check(self, contacts, *, rising):
        if not contacts:
            self.active=False
            self.previous={}
            return []
        if not rising or not self.active:
            return contacts
        rejected=[r for r in contacts if key(r) not in self.previous or
                  r['distance']<self.previous[key(r)]-NUMERIC_DISTANCE_M]
        self.previous=depths(contacts)
        return rejected
