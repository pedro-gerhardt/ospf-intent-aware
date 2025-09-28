class Router:
    def __init__(self, name: str):
        self.name = name
        self.neighbors: Dict[str, Dict[str, int]] = {} 

    def add_neighbor(self, neighbor: str, cost: int, latency: int, bandwidth: int):
        self.neighbors[neighbor] = {"cost": cost, "latency": latency, "bandwidth": bandwidth}

