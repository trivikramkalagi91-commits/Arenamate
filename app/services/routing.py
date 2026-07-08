"""Dijkstra routing logic over the arena sector connection graph.

Computes the shortest path using a standard Dijkstra algorithm with custom step-free constraints.
"""

from __future__ import annotations

import heapq

from app.services.arena_data import Arena, Link


def compute_shortest_path(
    arena: Arena, start: str, goal: str, *, step_free_only: bool = False
) -> list[Link] | None:
    """Find the path from `start` to `goal` with the minimum cumulative distance.

    Args:
        arena (Arena): The current Arena in-memory database instance.
        start (str): The starting sector ID.
        goal (str): The target sector ID.
        step_free_only (bool): If True, restricts calculations to step-free connections. Defaults to False.

    Returns:
        list[Link] | None: A list of Links representing the shortest path,
                           an empty list if start == goal, or None if no path exists.
    """
    if start == goal:
        return []
    if start not in arena.sectors or goal not in arena.sectors:
        return None

    # Priority queue storing tuples of (cumulative_distance, sector_id).
    frontier: list[tuple[int, str]] = [(0, start)]
    best_cost: dict[str, int] = {start: 0}
    came_from: dict[str, tuple[str, Link]] = {}

    while frontier:
        cost, node = heapq.heappop(frontier)
        if node == goal:
            return _rebuild_path(came_from, goal)
        if cost > best_cost.get(node, float("inf")):
            continue

        for edge in arena.neighbors(node):
            if step_free_only and not edge.step_free:
                continue
            new_cost = cost + edge.distance
            if new_cost < best_cost.get(edge.to, float("inf")):
                best_cost[edge.to] = new_cost
                came_from[edge.to] = (node, edge)
                heapq.heappush(frontier, (new_cost, edge.to))

    return None


def _rebuild_path(came_from: dict[str, tuple[str, Link]], goal: str) -> list[Link]:
    """Walk backwards from the goal to start, reconstructing the link path.

    Args:
        came_from (dict[str, tuple[str, Link]]): A mapping of sector ID -> (predecessor ID, connection Link).
        goal (str): The destination sector ID.

    Returns:
        list[Link]: The reconstructed list of connection Links from start to goal.
    """
    path: list[Link] = []
    node = goal
    while node in came_from:
        prev, edge = came_from[node]
        path.append(edge)
        node = prev
    path.reverse()
    return path


def path_distance(path: list[Link]) -> int:
    """Total length of the path in meters.

    Args:
        path (list[Link]): The list of connection Links in the path.

    Returns:
        int: The sum of connections distances in meters.
    """
    return sum(link.distance for link in path)
