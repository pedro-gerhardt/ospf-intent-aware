#!/usr/bin/env python3
import argparse, socket, json, threading, time, random
from collections import defaultdict
import heapq

# ---------------------------
# LSA + Intent
# ---------------------------
class LSA:
    def __init__(self, origin, neighbors):
        self.origin = origin
        self.neighbors = neighbors
        self.seq = random.randint(0, 100000)

    def to_json(self):
        return json.dumps({
            "origin": self.origin,
            "neighbors": self.neighbors,
            "seq": self.seq
        }).encode()

    @staticmethod
    def from_json(data):
        d = json.loads(data.decode())
        lsa = LSA(d["origin"], d["neighbors"])
        lsa.seq = d["seq"]
        return lsa

class Intent:
    def __init__(self, src, dst, max_latency=None, min_bandwidth=None):
        self.src, self.dst = src, dst
        self.max_latency = max_latency
        self.min_bandwidth = min_bandwidth

# ---------------------------
# Router process
# ---------------------------
class Router:
    def __init__(self, name, peers, port=10000):
        self.name = name
        self.port = port + int(name[1:])  # r1→10001, r2→10002...
        self.peers = peers
        self.lsdb = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", self.port))

    def originate_lsa(self):
        # For simplicity, use static neighbors (same as peer list)
        neighbors = {p: {"cost": 1, "latency": 5, "bandwidth": 100}
                     for p in self.peers}
        return LSA(self.name, neighbors)

    def flood(self, lsa):
        for p in self.peers:
            dst_port = 10000 + int(p[1:])
            self.sock.sendto(lsa.to_json(), ("127.0.0.1", dst_port))

    def receive_loop(self):
        while True:
            data, _ = self.sock.recvfrom(4096)
            lsa = LSA.from_json(data)
            # Simple seq check
            if (lsa.origin not in self.lsdb) or (lsa.seq > self.lsdb[lsa.origin].seq):
                self.lsdb[lsa.origin] = lsa
                self.flood(lsa)

    def compute_path(self, intent: Intent):
        graph = defaultdict(list)
        for lsa in self.lsdb.values():
            for nbr, m in lsa.neighbors.items():
                graph[lsa.origin].append((nbr, m["cost"], m["latency"], m["bandwidth"]))

        pq = [(0, 0, intent.src, [intent.src])]
        visited = set()
        while pq:
            cost, latency, node, path = heapq.heappop(pq)
            if node == intent.dst:
                return path
            if (node, latency) in visited:
                continue
            visited.add((node, latency))
            for (nbr, ncost, nlat, nband) in graph[node]:
                if intent.min_bandwidth and nband < intent.min_bandwidth:
                    continue
                new_latency = latency + nlat
                if intent.max_latency and new_latency > intent.max_latency:
                    continue
                heapq.heappush(pq, (cost+ncost, new_latency, nbr, path+[nbr]))
        return None

    def run(self):
        # Start listener thread
        threading.Thread(target=self.receive_loop, daemon=True).start()
        # Originate & flood LSAs
        while True:
            lsa = self.originate_lsa()
            self.lsdb[self.name] = lsa
            self.flood(lsa)
            # Example: compute path A→E
            if self.name == "r1":
                intent = Intent("r1", "r5", max_latency=25, min_bandwidth=50)
                path = self.compute_path(intent)
                if path:
                    print(f"{self.name}: Path {intent.src}->{intent.dst} = {path}")
            time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--peers", nargs="+", default=[])
    args = parser.parse_args()

    print(args)
    r = Router(args.name, args.peers)
    r.run()
