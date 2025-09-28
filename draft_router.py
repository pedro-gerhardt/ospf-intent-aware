from src.router import Router

a = Router("A")
b = Router("B")
c = Router("C")
d = Router("D")


def connectRouters(r1: Router, r2: Router, cost: int, latency: int, bandwidth: int):
    r1.add_neighbor(r2, cost, latency, bandwidth)
    r2.add_neighbor(r1, cost, latency, bandwidth)

connectRouters(a, b, cost=1, latency=5, bandwidth=100)
connectRouters(b, c, cost=1, latency=5, bandwidth=50)
connectRouters(a, c, cost=10, latency=2, bandwidth=100)
connectRouters(c, d, cost=1, latency=1, bandwidth=200)

print(a.neighbors)