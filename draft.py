from typing import Dict, List, Tuple, Optional
import heapq


class Link:
    def __init__(self, target: str, cost: int, latency: int, bandwidth: int):
        self.target = target
        self.cost = cost
        self.latency = latency
        self.bandwidth = bandwidth

class Graph:
    def __init__(self):
        self.adj: Dict[str, List[Link]] = {}

    def add_link(self, u: str, v: str, cost: int, latency: int, bandwidth: int):
        self.adj.setdefault(u, []).append(Link(v, cost, latency, bandwidth))
        self.adj.setdefault(v, []).append(Link(u, cost, latency, bandwidth))


class Intent:
    def __init__(self, src: str, dst: str,
                 max_latency: Optional[int] = None,
                 min_bandwidth: Optional[int] = None):
        self.src = src
        self.dst = dst
        self.max_latency = max_latency
        self.min_bandwidth = min_bandwidth


def spf(graph: Graph, intent: Intent) -> Optional[List[str]]:
    pq = [(0, 0, intent.src, [intent.src])]  # (cost, latency, node, path)
    visited = set()

    while pq:
        cost, latency, node, path = heapq.heappop(pq)
        if node == intent.dst:
            return path

        if (node, latency) in visited:
            continue
        visited.add((node, latency))

        for link in graph.adj.get(node, []):
            if intent.min_bandwidth and link.bandwidth < intent.min_bandwidth:
                continue
            new_latency = latency + link.latency
            if intent.max_latency and new_latency > intent.max_latency:
                continue
            heapq.heappush(pq, (cost + link.cost, new_latency, link.target, path + [link.target]))
    return None


g = Graph()
g.add_link("A", "B", cost=1, latency=5, bandwidth=100)
g.add_link("B", "C", cost=1, latency=5, bandwidth=50)
g.add_link("A", "C", cost=10, latency=2, bandwidth=100)
g.add_link("C", "D", cost=1, latency=1, bandwidth=200)

intent = Intent("A", "D", max_latency=12, min_bandwidth=40)
path = spf(g, intent)
print(path)
