from src.network import Network
from src.router import Router

net = Network()

for name in ["A", "B", "C", "D"]:
    net.add_router(Router(name))

net.connect("A", "B", cost=1, latency=5, bandwidth=100)
net.connect("B", "C", cost=1, latency=5, bandwidth=50)
net.connect("A", "C", cost=10, latency=2, bandwidth=10)
net.connect("C", "D", cost=1, latency=1, bandwidth=200)

net.flood_all()
