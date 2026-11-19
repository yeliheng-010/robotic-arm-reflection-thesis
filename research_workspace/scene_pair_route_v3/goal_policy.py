"""固定搜索边界；不根据案例编号调整参数。"""
EDGE_MARGIN_M = .020
BOTTOM_GAPS_M = (.010, .040, .070)
GRID = ((0,0),(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1))
MAX_PREFIX = 256
MAX_CARRY = 512


def usable_half(interior, extent):
    result=[float(a-b-EDGE_MARGIN_M) for a,b in zip(interior,extent)]
    if len(result)!=2 or min(result)<=0:
        raise ValueError('Object does not fit the registered interior margin')
    return result
