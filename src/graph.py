from typing import Dict, List
from src.link import Link

class Graph:
    def __init__(self):
        self.adj: Dict[str, List[Link]] = {}

    def add_link(self, u: str, v: str, cost: int, latency: int, bandwidth: int):
        self.adj.setdefault(u, []).append(Link(v, cost, latency, bandwidth))
        self.adj.setdefault(v, []).append(Link(u, cost, latency, bandwidth))