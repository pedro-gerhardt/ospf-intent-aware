from src.lsa import LSA
from typing import Dict, Optional, List
from src.intent import Intent
import heapq

class Router:
    def __init__(self, name: str):
        self.name = name
        self.neighbors: Dict[str, Dict[str, int]] = {} 
        self.lsdb: Dict[str, LSA] = {}
        self.received_ids: Set[str] = set()
        self.routing_table: Dict[Tuple[str, str], List[str]] = {}
        self.network: Optional["Network"] = None

    def add_neighbor(self, neighbor: str, cost: int, latency: int, bandwidth: int):
        self.neighbors[neighbor] = {"cost": cost, "latency": latency, "bandwidth": bandwidth}

    def originate_lsa(self) -> LSA:
        return LSA(self.name, self.neighbors)

    def flood(self, lsa: LSA, from_neighbor: Optional[str] = None):
        if lsa.id in self.received_ids:
            return
        self.received_ids.add(lsa.id)
        self.lsdb[lsa.origin] = lsa
        
        for nbr in self.neighbors: 
            if nbr != from_neighbor: # forward to all except the sender
                self.network.deliver(nbr, lsa, self.name)
    
    def compute_path(self, intent: Intent) -> Optional[List[str]]:
        graph: Dict[str, List[Tuple[str, int, int, int]]] = {}
        for lsa in self.lsdb.values():
            for nbr, metrics in lsa.neighbors.items():
                graph.setdefault(lsa.origin, []).append(
                    (nbr, metrics["cost"], metrics["latency"], metrics["bandwidth"])
                )

        pq = [(0, 0, intent.src, [intent.src])] # (cost, latency, node, path)
        visited = set()

        while pq:
            cost, latency, node, path = heapq.heappop(pq)
            if node == intent.dst:
                return path

            if (node, latency) in visited:
                continue
            visited.add((node, latency))

            for (nbr, ncost, nlat, nband) in graph.get(node, []):
                if intent.min_bandwidth and nband < intent.min_bandwidth:
                    continue
                new_latency = latency + nlat
                if intent.max_latency and new_latency > intent.max_latency:
                    continue
                heapq.heappush(
                    pq, (cost + ncost, new_latency, nbr, path + [nbr])
                )
        return None

    def run_spf(self, intent: Intent):
        path = self.compute_path(intent)
        if path:
            self.routing_table[(intent.src, intent.dst)] = path