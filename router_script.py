#!/usr/bin/env python3
import argparse, socket, json, threading, time
from collections import defaultdict
import heapq
import subprocess
import re

class LSA:
    def __init__(self, origin, links, seq=None):
        self.origin = origin
        self.links = links
        self.seq = seq if seq is not None else int(time.time())

    def to_json(self):
        return json.dumps({"origin": self.origin, "links": self.links, "seq": self.seq}).encode()

    @staticmethod
    def from_json(data):
        d = json.loads(data.decode())
        return LSA(d["origin"], d["links"], d["seq"])

class Intent:
    def __init__(self, src, dst, max_latency=None, min_bandwidth=None):
        self.src, self.dst = src, dst
        self.max_latency = max_latency
        self.min_bandwidth = min_bandwidth

    def __str__(self):
        constraints = []
        if self.max_latency is not None:
            constraints.append(f"max_latency <= {self.max_latency}ms")
        if self.min_bandwidth is not None:
            constraints.append(f"min_bw >= {self.min_bandwidth}Mbps")

        if not constraints:
            return f"Intent[{self.src} -> {self.dst}] (No constraints)"
        
        return f"Intent[{self.src} -> {self.dst}], Constraints: [{', '.join(constraints)}]"

    def __repr__(self):
        return (f"Intent(src={self.src!r}, dst={self.dst!r}, "
                f"max_latency={self.max_latency!r}, min_bandwidth={self.min_bandwidth!r})")


class Router:
    def __init__(self, name, port_base=10000, control_base=20000):
        self.name = name
        self.port = port_base + int(name[1:])
        self.links = {}
        self.stub_networks = {} # Dicionário para redes stub (conectadas a PCs)
        self.peer_ports = {}
        self.lsdb = {}
        self.connected_subnets = set()
        self.active_neighbors = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.port))
        self.intents = {}
        self.control_port = control_base + int(name[1:])
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_sock.bind(("0.0.0.0", self.control_port))

    def add_intent(self, src, dst, max_latency=None, min_bandwidth=None):
        self.intents[(src, dst)] = Intent(src, dst, max_latency, min_bandwidth)
        print(f"[{self.name}] Intent adicionada: {src}->{dst}, "
              f"max_latency={max_latency}, min_bw={min_bandwidth}")

    def control_loop(self):
        while True:
            try:
                data, addr = self.control_sock.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg.get("type") == "INTENT":
                    src, dst = msg.get("src"), msg.get("dst")
                    max_lat = msg.get("max_latency")
                    min_bw = msg.get("min_bandwidth")
                    self.add_intent(src, dst, max_latency=max_lat, min_bandwidth=min_bw)
                    self.update_routing_table()
            except Exception as e:
                print(f"[{self.name}] Erro no control_loop: {e}")

    def add_link_info(self, peer_name, peer_ip, subnet, cost, latency, bandwidth, peer_port):
        self.links[peer_name] = {
            "peer_ip": peer_ip, "subnet": subnet,
            "cost": int(cost), "latency": int(latency), "bandwidth": int(bandwidth),
            "up": True
        }
        self.peer_ports[peer_name] = int(peer_port)
        self.connected_subnets.add(subnet)

    def find_router_for_host(self, hostname):
        """
        Encontra o nome do roteador que anuncia a sub-rede de um host (ex: 'pc1').
        Ele faz isso procurando no LSDB por um roteador que tenha a sub-rede correspondente
        como um link "stub". Ex: pc1 -> 172.16.1.0/24.
        """
        match = re.match(r'pc(\d+)', hostname)
        if not match:
            return None # Não é um nome de host de PC que conhecemos

        pc_id = match.group(1)
        target_subnet = f"172.16.{pc_id}.0/24"

        print("target_subnet:", target_subnet)

        for router_name, lsa in self.lsdb.items():
            for link_info in lsa.links.values():
                print("link_info:", link_info)
                # Verifica se o link é uma rede stub e se a sub-rede bate
                if link_info.get("stub") and link_info.get("subnet") == target_subnet:
                    return router_name
        return None

    def add_stub_network(self, subnet, cost):
        """Adiciona uma rede stub (com PCs) que deve ser anunciada."""
        self.stub_networks[subnet] = {
            "subnet": subnet, "cost": int(cost), "stub": True
        }
        self.connected_subnets.add(subnet)
        print(f"[{self.name}] Rede stub configurada: {subnet}")

    def send_message(self, msg_type, payload, peer_ip, peer_port, peer_name=None):
        msg = json.dumps({"type": msg_type, "payload": payload}).encode()
            # Registra o envio de um pacote, seu tipo, tamanho e destino.
        print(f"[{self.name}] METRIC_PACKET_SENT type={msg_type} size={len(msg)} to={peer_ip}:{peer_port}")
        try:
            self.sock.sendto(msg, (peer_ip, peer_port))
        except OSError as e:
            if peer_name and peer_name in self.links:
                self.links[peer_name]["up"] = False

    def parse_message(self, data):
        d = json.loads(data.decode())
        return d["type"], d["payload"]

    def send_hello(self):
        for peer_name, peer_port in self.peer_ports.items():
            if peer_name in self.links and self.links[peer_name]["up"]:
                peer_ip = self.links[peer_name]["peer_ip"]
                print(f"[{self.name}] Gerando HELLO para {peer_name} ({peer_ip}:{peer_port})")
                self.send_message("HELLO", {"from": self.name}, peer_ip, peer_port, peer_name=peer_name)

    def originate_lsa(self):
        """Cria o LSA deste roteador com base em seus links ativos e redes stub."""
        active_peers = self.get_active_neighbors()
        active_links = {peer: self.links[peer] for peer in active_peers if peer in self.links}
        
        # Adiciona as redes stub ao LSA para que sejam anunciadas
        all_advertised_links = {**active_links, **self.stub_networks}

        print(f"[{self.name}] Gerando LSA com {len(active_links)} vizinhos ativos e {len(self.stub_networks)} redes stub.")
        return LSA(self.name, all_advertised_links)

    def flood(self, lsa, from_peer=None):
        for peer_name, peer_port in self.peer_ports.items():
            if peer_name != from_peer and peer_name in self.links:
                peer_ip = self.links[peer_name]['peer_ip']
                self.send_message("LSA", lsa.to_json().decode(), peer_ip, peer_port, peer_name=peer_name)

    def get_active_neighbors(self, timeout=15):
        now = time.time()
        for n, last_hello in list(self.active_neighbors.items()):
            if now - last_hello > timeout:
                print(f"[{self.name}] Vizinho {n} considerado INATIVO.")
                if n in self.links:
                    self.links[n]["up"] = False
                del self.active_neighbors[n]
        return list(self.active_neighbors.keys())

    def receive_loop(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                msg_type, payload = self.parse_message(data)

                if msg_type == "HELLO":
                    sender = payload["from"]
                    if sender not in self.active_neighbors:
                        print(f"[{self.name}] Novo vizinho ativo detectado: {sender}")
                    self.active_neighbors[sender] = time.time()
                    if sender in self.links:
                        self.links[sender]["up"] = True
                    continue

                elif msg_type == "LSA":
                    lsa = LSA.from_json(payload.encode())
                    from_peer = next((n for n, p in self.peer_ports.items() if (self.links.get(n) and self.links[n]['peer_ip'] == addr[0])), None)

                    if (lsa.origin not in self.lsdb) or (lsa.seq > self.lsdb[lsa.origin].seq):
                        print(f"[{self.name}] Recebeu novo LSA de {lsa.origin} via {from_peer}. Inundando...")
                        self.lsdb[lsa.origin] = lsa
                        self.flood(lsa, from_peer=from_peer)
                    continue
            except Exception as e:
                print(f"[{self.name}] Erro no loop de recebimento: {e}")


    def update_routing_table(self):
        print(f"[{self.name}] Atualizando tabela de roteamento...")
        graph = defaultdict(list)
        for router_name, lsa in self.lsdb.items():
            for key, metrics in lsa.links.items():
                if metrics.get("stub") or not metrics.get("up", True):
                    continue
                graph[router_name].append((key, metrics))
        
        all_remote_subnets = set()
        for lsa in self.lsdb.values():
            for link_info in lsa.links.values():
                all_remote_subnets.add(link_info["subnet"])
                
        for dest_subnet in all_remote_subnets:
            if dest_subnet in self.connected_subnets:
                continue
            
            dest_router_name = next((name for name, lsa in self.lsdb.items() if any(link['subnet'] == dest_subnet for link in lsa.links.values())), None)
            
            if not dest_router_name:
                continue

            applicable_intent = None
            # Itera sobre todas as intents armazenadas
            for intent in self.intents.values():
                # Para cada intent, descobre qual roteador está conectado ao host de destino
                intent_dest_router = self.find_router_for_host(intent.dst)
                
                # Se o roteador de destino da intent for o mesmo para o qual estamos calculando a rota agora...
                if intent_dest_router == dest_router_name:
                    # ... então encontramos a intent correta a ser aplicada.
                    applicable_intent = intent
                    print(f"[{self.name}] Intent para {intent.src}->{intent.dst} é aplicável para a rota até {dest_router_name}. Aplicando restrições.")
                    break
            
            path = None
            if applicable_intent:
                # 1. Primeira tentativa: Tenta encontrar um caminho que satisfaça a intent
                print(f"[{self.name}] Tentando encontrar caminho para {dest_router_name} com a intent: {applicable_intent}")
                path_intent = Intent(self.name, dest_router_name, 
                                     applicable_intent.max_latency, 
                                     applicable_intent.min_bandwidth)
                path = self.compute_path(path_intent, graph)

            # 2. Segunda tentativa (Fallback): Se a primeira tentativa falhou, ou se não havia intent...
            if not path:
                # Se entramos aqui porque a tentativa com intent falhou, imprime uma mensagem de aviso
                if applicable_intent:
                    print(f"[{self.name}] AVISO: Não foi possível encontrar um caminho para {dest_router_name} que satisfaça a intent.")
                
                print(f"[{self.name}] Calculando o melhor caminho para {dest_router_name} sem restrições.")
                # Calcula o caminho sem nenhuma restrição
                default_intent = Intent(self.name, dest_router_name)
                path = self.compute_path(default_intent, graph)

            if path and len(path) > 1:
                next_hop_router = path[1]
                if next_hop_router in self.links:
                    next_hop_ip = self.links[next_hop_router]['peer_ip']
                    print(f"[{self.name}] Rota para {dest_subnet}: próximo salto é {next_hop_router} ({next_hop_ip})")
                    cmd = f"ip route replace {dest_subnet} via {next_hop_ip}"
                    try:
                        subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    except subprocess.CalledProcessError as e:
                        print(f"[{self.name}] Erro ao instalar rota para {dest_subnet}: {e.stderr.decode().strip()}")
        
        try:
            result = subprocess.run("ip route | wc -l", shell=True, check=True, capture_output=True, text=True)
            table_size = int(result.stdout.strip())
            print(f"[{self.name}] METRIC_TABLE_SIZE size={table_size}")
        except subprocess.CalledProcessError as e:
            print(f"[{self.name}] Erro ao obter tamanho da tabela de roteamento: {e.stderr.strip()}")


    def compute_path(self, intent: Intent, graph: dict):
        pq = [(0, 0, intent.src, [intent.src])]
        min_costs = {intent.src: 0}
        
        while pq:
            cost, latency, node, path = heapq.heappop(pq)
            if cost > min_costs.get(node, float('inf')):
                continue
            if node == intent.dst:
                return path

            for (nbr, metrics) in graph.get(node, []):
                n_cost = metrics.get("cost", 1)
                n_lat = metrics.get("latency", 0)
                n_band = int(metrics.get("bandwidth", 0))
                
                if intent.min_bandwidth and n_band < intent.min_bandwidth:
                    continue
                new_cost = cost + n_cost
                new_latency = latency + n_lat
                if intent.max_latency and new_latency > intent.max_latency:
                    continue
                if new_cost < min_costs.get(nbr, float('inf')):
                    min_costs[nbr] = new_cost
                    heapq.heappush(pq, (new_cost, new_latency, nbr, path + [nbr]))
        return None

    def run(self):
        print(f"[{self.name}] Daemon iniciado. Vizinhos: {list(self.peer_ports.keys())}")
        threading.Thread(target=self.receive_loop, daemon=True).start()
        threading.Thread(target=self.control_loop, daemon=True).start()
        time.sleep(2)
        
        while True:
            self.send_hello()
            current_lsa = self.originate_lsa()
            self.lsdb[self.name] = current_lsa
            self.flood(current_lsa)
            
            print(f"[{self.name}] LSDB contém {len(self.lsdb)} entradas.")
            
            if self.lsdb:
                self.update_routing_table()
            
            time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--links", nargs=7, action='append', help="Link para outro roteador")
    parser.add_argument("--stub-network", nargs=2, action='append', help="Rede local a ser anunciada")
    args = parser.parse_args()

    router = Router(args.name)
    if args.links:
        for link_info in args.links:
            router.add_link_info(*link_info)
    
    if args.stub_network:
        for subnet, cost in args.stub_network:
            router.add_stub_network(subnet, cost)
    
    router.run()