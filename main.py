from typing import Dict, List, Tuple, Optional
import heapq
from link import Link
from graph import Graph
from intent import Intent


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
