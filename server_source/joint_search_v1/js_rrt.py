"""预算受限的RRT-Connect；逆向树也按实际执行方向检查每条边。"""
import math
import random
import time

GOAL_BIAS = .15
EPS = 1e-12


class BudgetStop(Exception):
    pass


def validate(start, goal, options):
    bounds = options['bounds']
    if not start or len(start) != len(goal) or len(start) != len(bounds):
        raise ValueError('Mismatched dimensions')
    values = [*start, *goal, *[v for pair in bounds for v in pair],
              options['step'], options['seconds']]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Finite values required')
    if options['step'] <= 0 or options['seconds'] <= 0:
        raise ValueError('Positive step and duration required')
    for key, minimum in (('max_checks', 1), ('max_nodes', 2)):
        if type(options[key]) is not int or options[key] < minimum:
            raise ValueError('Invalid '+key)
    for a, b, (low, high) in zip(start, goal, bounds):
        if not low < high or not low <= a <= high or not low <= b <= high:
            raise ValueError('Invalid bounds or endpoint')


class Budget:
    def __init__(self, options):
        self.options = options
        self.clock = options['clock']
        self.started = self.clock()
        self.checks, self.nodes = 0, 2

    def deadline(self):
        if self.clock()-self.started >= self.options['seconds']:
            raise BudgetStop('time_budget')

    def edge(self, start, goal):
        self.deadline()
        if self.checks >= self.options['max_checks']:
            raise BudgetStop('check_budget')
        self.checks += 1
        result = self.options['check'](list(start), list(goal))
        if type(result) is not bool:
            raise TypeError('Guard must return bool')
        callback = self.options['on_check']
        if callback:
            callback(dict(index=self.checks, start=list(start), goal=list(goal), accepted=result))
        self.deadline()
        return result


class Tree:
    def __init__(self, root, *, reverse):
        self.points, self.parents = [list(root)], [None]
        self.reverse = reverse

    def extend(self, target, budget):
        budget.deadline()
        if budget.nodes >= budget.options['max_nodes']:
            raise BudgetStop('node_budget')
        index = min(range(len(self.points)), key=lambda i: math.dist(self.points[i], target))
        start = self.points[index]
        distance = math.dist(start, target)
        if distance < EPS:
            return 'reached', index
        scale = min(1., budget.options['step']/distance)
        goal = list(target) if scale == 1. else [a+(b-a)*scale for a,b in zip(start,target)]
        valid = budget.edge(goal,start) if self.reverse else budget.edge(start,goal)
        if not valid:
            return 'trapped', None
        self.points.append(goal)
        self.parents.append(index)
        budget.nodes += 1
        return ('reached' if scale == 1. else 'advanced'), len(self.points)-1

    def connect(self, target, budget):
        status, index = self.extend(target, budget)
        while status == 'advanced':
            status, index = self.extend(target, budget)
        return status, index

    def trace(self, index):
        path = []
        while index is not None:
            path.append(self.points[index])
            index = self.parents[index]
        return path[::-1]


def join(first, second, *, a, b):
    if first.reverse:
        return second.trace(b)+first.trace(a)[-2::-1]
    return first.trace(a)+second.trace(b)[-2::-1]


def grow(start, goal, budget):
    if budget.edge(start,goal):
        return [list(start), list(goal)]
    first, second = Tree(start,reverse=False), Tree(goal,reverse=True)
    rng = random.Random(budget.options['seed'])
    while True:
        target = second.points[0] if rng.random() < GOAL_BIAS else [
            rng.uniform(low,high) for low,high in budget.options['bounds']]
        status, index = first.extend(target,budget)
        if status != 'trapped':
            state, other = second.connect(first.points[index],budget)
            if state == 'reached':
                return join(first,second,a=index,b=other)
        first, second = second, first


def search(start, goal, *, bounds, check, seed, step, max_checks, max_nodes,
           seconds, clock=time.monotonic, on_check=None):
    options = dict(bounds=bounds,check=check,seed=seed,step=step,max_checks=max_checks,
                   max_nodes=max_nodes,seconds=seconds,clock=clock,on_check=on_check)
    validate(start,goal,options)
    budget = Budget(options)
    path, status = None, 'found'
    try:
        path = grow(start,goal,budget)
    except BudgetStop as error:
        status = str(error)
    return dict(status=status,path=path,checks=budget.checks,nodes=budget.nodes)
