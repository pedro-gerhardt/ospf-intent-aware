from typing import Optional

class Intent:
    def __init__(self, src: str, dst: str,
                 max_latency: Optional[int] = None,
                 min_bandwidth: Optional[int] = None):
        self.src = src
        self.dst = dst
        self.max_latency = max_latency
        self.min_bandwidth = min_bandwidth