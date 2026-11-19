from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


Point2 = Tuple[float, float]
Cell = Tuple[int, int]
Rectangle = Tuple[float, float, float, float]


@dataclass(frozen=True)
class GridSpec:
    x_min: float = 0.0
    x_max: float = 6.0
    y_min: float = 0.0
    y_max: float = 4.0
    resolution: float = 0.1
    robot_radius: float = 0.28


class AStarNavigator:
    def __init__(self, spec: GridSpec = GridSpec()) -> None:
        self.spec = spec

    def plan(
        self,
        start: Point2,
        goal: Point2,
        obstacles: Sequence[Rectangle],
    ) -> List[Point2]:
        inflated = [self._inflate(rectangle) for rectangle in obstacles]
        start_cell = self._to_cell(start)
        goal_cell = self._to_cell(goal)
        blocked = self._blocked_cells(inflated)
        blocked.discard(start_cell)
        blocked.discard(goal_cell)
        cell_path = self._a_star(start_cell, goal_cell, blocked)
        if not cell_path:
            return []
        points = [self._to_point(cell) for cell in cell_path]
        points[0] = start
        points[-1] = goal
        return self._simplify(points, inflated)

    def path_is_clear(
        self, path: Sequence[Point2], obstacles: Sequence[Rectangle]
    ) -> bool:
        inflated = [self._inflate(rectangle) for rectangle in obstacles]
        for first, second in zip(path, path[1:]):
            if not self._segment_clear(first, second, inflated):
                return False
        return True

    def _a_star(self, start: Cell, goal: Cell, blocked: set[Cell]) -> List[Cell]:
        frontier: List[Tuple[float, Cell]] = [(0.0, start)]
        came_from: Dict[Cell, Optional[Cell]] = {start: None}
        cost_so_far: Dict[Cell, float] = {start: 0.0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break
            for neighbor, move_cost in self._neighbors(current):
                if neighbor in blocked or not self._inside(neighbor):
                    continue
                new_cost = cost_so_far[current] + move_cost
                if new_cost >= cost_so_far.get(neighbor, float("inf")):
                    continue
                cost_so_far[neighbor] = new_cost
                priority = new_cost + math.dist(neighbor, goal)
                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current

        if goal not in came_from:
            return []
        path = []
        cursor: Optional[Cell] = goal
        while cursor is not None:
            path.append(cursor)
            cursor = came_from[cursor]
        return list(reversed(path))

    @staticmethod
    def _neighbors(cell: Cell) -> Iterable[Tuple[Cell, float]]:
        x, y = cell
        for dx, dy in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ):
            yield (x + dx, y + dy), math.sqrt(2.0) if dx and dy else 1.0

    def _blocked_cells(self, obstacles: Sequence[Rectangle]) -> set[Cell]:
        blocked: set[Cell] = set()
        nx = int(round((self.spec.x_max - self.spec.x_min) / self.spec.resolution))
        ny = int(round((self.spec.y_max - self.spec.y_min) / self.spec.resolution))
        for x in range(nx + 1):
            for y in range(ny + 1):
                px, py = self._to_point((x, y))
                if any(x1 <= px <= x2 and y1 <= py <= y2 for x1, y1, x2, y2 in obstacles):
                    blocked.add((x, y))
        return blocked

    def _inside(self, cell: Cell) -> bool:
        x, y = self._to_point(cell)
        return (
            self.spec.x_min <= x <= self.spec.x_max
            and self.spec.y_min <= y <= self.spec.y_max
        )

    def _to_cell(self, point: Point2) -> Cell:
        x, y = point
        return (
            int(round((x - self.spec.x_min) / self.spec.resolution)),
            int(round((y - self.spec.y_min) / self.spec.resolution)),
        )

    def _to_point(self, cell: Cell) -> Point2:
        return (
            self.spec.x_min + cell[0] * self.spec.resolution,
            self.spec.y_min + cell[1] * self.spec.resolution,
        )

    def _inflate(self, rectangle: Rectangle) -> Rectangle:
        x1, y1, x2, y2 = rectangle
        radius = self.spec.robot_radius
        return x1 - radius, y1 - radius, x2 + radius, y2 + radius

    @staticmethod
    def _segment_clear(
        start: Point2, end: Point2, obstacles: Sequence[Rectangle]
    ) -> bool:
        length = max(math.dist(start, end), 1e-6)
        samples = max(2, int(math.ceil(length / 0.04)))
        for index in range(samples + 1):
            alpha = index / samples
            x = start[0] + (end[0] - start[0]) * alpha
            y = start[1] + (end[1] - start[1]) * alpha
            if any(x1 <= x <= x2 and y1 <= y <= y2 for x1, y1, x2, y2 in obstacles):
                return False
        return True

    def _simplify(
        self, path: Sequence[Point2], obstacles: Sequence[Rectangle]
    ) -> List[Point2]:
        if len(path) <= 2:
            return list(path)
        simplified = [path[0]]
        anchor = 0
        while anchor < len(path) - 1:
            candidate = len(path) - 1
            while candidate > anchor + 1:
                if self._segment_clear(path[anchor], path[candidate], obstacles):
                    break
                candidate -= 1
            simplified.append(path[candidate])
            anchor = candidate
        return simplified
