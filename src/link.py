class Link:
    def __init__(self, target: str, cost: int, latency: int, bandwidth: int):
        self.target = target
        self.cost = cost
        self.latency = latency
        self.bandwidth = bandwidth