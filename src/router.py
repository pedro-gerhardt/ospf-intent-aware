from src.lsa import LSA
from typing import Dict, Optional

class Router:
    def __init__(self, name: str):
        self.name = name
        self.neighbors: Dict[str, Dict[str, int]] = {} 
        self.lsdb: Dict[str, LSA] = {}
        self.received_ids: Set[str] = set()

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