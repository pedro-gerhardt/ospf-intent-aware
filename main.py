from src.network import Network
from src.router import Router
from src.intent import Intent

import random

if __name__ == "__main__":
    net = Network()

    names = ["A", "B", "C", "D", "E"]
    for name in names:
        net.add_router(Router(name))

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if random.random() < 0.6:   
                cost = random.randint(1, 10)
                latency = random.randint(1, 10)
                bandwidth = random.randint(10, 200)
                net.connect(names[i], names[j], cost, latency, bandwidth)
                print(f"Connected {names[i]}-{names[j]} "
                      f"(cost={cost}, lat={latency}, bw={bandwidth})")

    net.flood_all()

    for r in net.routers.values():
        for src in names:
            for dst in names:
                if src != dst:
                    intent = Intent(src, dst)
                    r.run_spf(intent)

    for r in net.routers.values():
        print(f"\n=== Router {r.name} Routing Table ===")
        for (src, dst), path in sorted(r.routing_table.items()):
            print(f" {src}->{dst}: {' -> '.join(path)}")
