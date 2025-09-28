from src.router import Router
from src.lsa import LSA

class Network:
    def __init__(self):
        self.routers: Dict[str, Router] = {}

    def add_router(self, r: Router):
        r.network = self
        self.routers[r.name] = r

    def connect(self, a: str, b: str, cost: int, latency: int, bandwidth: int):
        self.routers[a].add_neighbor(b, cost, latency, bandwidth)
        self.routers[b].add_neighbor(a, cost, latency, bandwidth)
    
    def flood_all(self):
        for r in self.routers.values():
            lsa = r.originate_lsa()
            r.flood(lsa)

    def deliver(self, to: str, lsa: LSA, from_router: str):
        self.routers[to].flood(lsa, from_neighbor=from_router)