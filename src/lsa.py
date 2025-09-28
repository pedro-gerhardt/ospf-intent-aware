from typing import Dict
import uuid

class LSA:
    def __init__(self, origin: str, neighbors: Dict[str, Dict[str, int]]):
        self.id = str(uuid.uuid4())
        self.origin = origin
        self.neighbors = neighbors

    def __repr__(self):
        return f"LSA(origin={self.origin}, neighbors={self.neighbors})" 