#!/usr/bin/env python3
import argparse, socket, json, threading, time
from collections import defaultdict
import heapq
import subprocess

# --- Definição das Estruturas de Dados ---

class LSA:
    """
    Representa um Link-State Advertisement (LSA).
    Um LSA é um pacote que descreve os links diretos de um roteador.
    """
    def __init__(self, origin, links, seq=None):
        self.origin = origin  # Nome do roteador que originou o LSA (ex: "r1").
        self.links = links    # Dicionário descrevendo os vizinhos e as métricas dos links.
        # Número de sequência para identificar a "idade" do LSA. LSAs mais novos têm 'seq' maior.
        self.seq = seq if seq is not None else int(time.time())

    def to_json(self):
        """Serializa o LSA para JSON para poder ser enviado pela rede."""
        return json.dumps({"origin": self.origin, "links": self.links, "seq": self.seq}).encode()

    @staticmethod
    def from_json(data):
        """Desserializa dados JSON para criar um objeto LSA."""
        d = json.loads(data.decode())
        return LSA(d["origin"], d["links"], d["seq"])

class Intent:
    """
    Representa uma "intenção" de roteamento, definindo restrições para o cálculo do caminho.
    Por exemplo, um caminho com latência máxima ou largura de banda mínima.
    """
    def __init__(self, src, dst, max_latency=None, min_bandwidth=None):
        self.src, self.dst = src, dst
        self.max_latency = max_latency
        self.min_bandwidth = min_bandwidth

# --- Classe Principal do Roteador ---

class Router:
    """
    Implementa a lógica do daemon de roteamento para um único roteador.
    """
    def __init__(self, name, port_base=10000):
        self.name = name
        self.port = port_base + int(name[1:])
        self.links = {}  # Armazena informações sobre os links diretos: {vizinho: {métricas}}.
        self.peer_ports = {} # Armazena as portas dos daemons vizinhos: {vizinho: porta}.
        self.lsdb = {}  # Link-State Database: armazena o LSA mais recente de cada roteador da rede.
        self.connected_subnets = set() # Conjunto de sub-redes diretamente conectadas.
        self.active_neighbors = {}  # { vizinho: timestamp_ultimo_hello }

        # Cria um socket UDP para comunicação com outros daemons.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Binda o socket a '0.0.0.0' para escutar em todas as interfaces de rede do namespace
        self.sock.bind(("0.0.0.0", self.port))

    def add_link_info(self, peer_name, peer_ip, subnet, cost, latency, bandwidth, peer_port):
        """Adiciona informações de um link direto, recebidas via argumento de linha de comando."""
        self.links[peer_name] = {
            "peer_ip": peer_ip, "subnet": subnet,
            "cost": int(cost), "latency": int(latency), "bandwidth": int(bandwidth),
            "up": True
        }
        self.peer_ports[peer_name] = int(peer_port)
        self.connected_subnets.add(subnet)

    def send_message(self, msg_type, payload, peer_ip, peer_port, peer_name=None):
        msg = json.dumps({"type": msg_type, "payload": payload}).encode()
        try:
            self.sock.sendto(msg, (peer_ip, peer_port))
        except OSError as e:
            print(f"[{self.name}] Erro ao enviar para {peer_ip}:{peer_port} -> {e}")
            # Se sabemos o vizinho, marcamos o link como down
            if peer_name and peer_name in self.links:
                self.links[peer_name]["up"] = False


    def parse_message(self, data):
        d = json.loads(data.decode())
        return d["type"], d["payload"]

    def send_hello(self):
        print("send hello - " + self.name)
        for peer_name, peer_port in self.peer_ports.items():
            if peer_name in self.links and self.links[peer_name]["up"]:
                peer_ip = self.links[peer_name]["peer_ip"]
                self.send_message("HELLO", {"from": self.name}, peer_ip, peer_port, peer_name=peer_name)


    def originate_lsa(self):
        """
        Cria o LSA deste roteador com base APENAS nos seus links ativos.
        """
        # 1. Descobre quais vizinhos estão realmente respondendo.
        # active_peers = self.check_neighbor_status()
        active_peers = self.get_active_neighbors()
        
        # 2. Cria um dicionário de links contendo apenas os vizinhos ativos.
        active_links = {peer: self.links[peer] for peer in active_peers if peer in self.links}        
        
        # 3. Gera o LSA com a informação atualizada e um novo timestamp/seq.
        print(f"[{self.name}] Gerando LSA com vizinhos ativos: {active_peers}")
        return LSA(self.name, active_links)

    def flood(self, lsa, from_peer=None):
        """
        Inunda (floods) um LSA para todos os vizinhos, exceto aquele de quem o LSA foi recebido.
        """
        for peer_name, peer_port in self.peer_ports.items():
            if peer_name != from_peer:
                # Obtém o IP real do vizinho para enviar o pacote para que a comunicação cruze os namespaces do Mininet.
                if peer_name in self.links:
                    peer_ip = self.links[peer_name]['peer_ip']
                    try:
                        self.send_message("LSA", lsa.to_json().decode(), peer_ip, peer_port)
                        # self.sock.sendto(lsa.to_json(), (peer_ip, peer_port))
                    except:
                        del self.links[peer_name]

    def get_active_neighbors(self, timeout=30):
        now = time.time()
        still_active = {}

        for n, last in self.active_neighbors.items():
            if now - last <= timeout:
                still_active[n] = last
            else:
                print(f"[{self.name}] Vizinho {n} considerado INATIVO (sem Hello há {int(now - last)}s).")
                if n in self.links:
                    self.links[n]["up"] = False  # marca link como down

        self.active_neighbors = still_active
        return list(still_active.keys())



    def receive_loop(self):
        """Loop executado em uma thread para receber mensagens (HELLO, LSA, ACK)."""
        while True:
            data, addr = self.sock.recvfrom(4096)
            print(addr, data)
            msg_type, payload = self.parse_message(data)

            # --- Tratamento de HELLO ---
            if msg_type == "HELLO":
                sender = payload["from"]

                # Marca vizinho como ativo
                if sender not in self.active_neighbors:
                    print(f"[{self.name}] Novo vizinho ativo detectado: {sender}")
                # self.active_neighbors.add(sender)
                self.active_neighbors[sender] = time.time()  # registra timestamp
                
                if sender in self.links:
                    self.links[sender]["up" ] = True
                # Responde com Hello de volta (bidirecionalidade)
                # if sender in self.links:
                #     peer_ip = self.links[sender]["peer_ip"]
                #     peer_port = self.peer_ports[sender]
                #     self.send_message("HELLO", {"from": self.name}, peer_ip, peer_port)
                continue

            # --- Tratamento de LSA ---
            elif msg_type == "LSA":
                lsa = LSA.from_json(payload.encode())

                # Identifica o vizinho que enviou o LSA pela porta de origem
                from_peer = next((n for n, p in self.peer_ports.items() if addr[1] == p), None)

                # Processa LSA apenas se for novo ou mais recente
                if (lsa.origin not in self.lsdb) or (lsa.seq > self.lsdb[lsa.origin].seq):
                    print(f"[{self.name}] Recebeu novo LSA de {lsa.origin} via {from_peer}. Inundando...")
                    self.lsdb[lsa.origin] = lsa
                    self.flood(lsa, from_peer=from_peer)

                # Envia ACK de volta para quem enviou
                if from_peer in self.links:
                    peer_ip = self.links[from_peer]["peer_ip"]
                    peer_port = self.peer_ports[from_peer]
                    self.send_message("ACK", {"origin": lsa.origin, "seq": lsa.seq}, peer_ip, peer_port)
                continue

            # --- Tratamento de ACK ---
            elif msg_type == "ACK":
                origin, seq = payload["origin"], payload["seq"]
                print(f"[{self.name}] Recebeu ACK confirmando LSA de {origin} (seq={seq})")
                continue


    # def receive_loop(self):
    #     """Loop executado em uma thread para receber LSAs de outros roteadores."""
    #     while True:
    #         data, addr = self.sock.recvfrom(4096)
    #         lsa = LSA.from_json(data)
    #         # Identifica o vizinho que enviou o LSA com base na porta de origem.
    #         from_peer = next((n for n, p in self.peer_ports.items() if addr[1] == p), None)
            
    #         # Processa o LSA apenas se for novo ou mais recente que a versão no LSDB.
    #         if (lsa.origin not in self.lsdb) or (lsa.seq > self.lsdb[lsa.origin].seq):
    #             print(f"[{self.name}] Recebeu novo LSA de {lsa.origin} via {from_peer}. Inundando...")
    #             self.lsdb[lsa.origin] = lsa # Atualiza o LSDB local.
    #             self.flood(lsa, from_peer=from_peer) # Re-inunda para outros vizinhos.
            
    def check_neighbor_status(self):
        """
        Verifica quais vizinhos estão ativamente respondendo a pings.
        Retorna uma lista com os nomes dos vizinhos ativos.
        """
        active_neighbors = []
        for peer_name, link_info in self.links.items():
            peer_ip = link_info['peer_ip']
            # Executa 'ping' com contagem 1 (-c 1) e timeout de 1 segundo (-W 1).
            # Redireciona a saída para /dev/null para não poluir o log.
            cmd = f"ping -c 1 -W 1 {peer_ip}"
            try:
                # O 'check=True' fará com que uma exceção seja lançada se o ping falhar (exit code != 0).
                subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                active_neighbors.append(peer_name)
            except subprocess.CalledProcessError:
                # Se o ping falhar, o vizinho é considerado inativo.
                print(f"[{self.name}] Alerta: Vizinho {peer_name} ({peer_ip}) está inacessível.")
        return active_neighbors
    
    def update_routing_table(self):
        """
        Calcula as melhores rotas usando o LSDB e atualiza a tabela de roteamento do kernel.
        """
        print(f"[{self.name}] Atualizando tabela de roteamento do kernel com {len(self.lsdb)} LSAs...")
        
        # 1. Constrói um grafo da topologia da rede a partir do LSDB.
        graph = defaultdict(list)
        for router_name, lsa in self.lsdb.items():
            for peer, metrics in lsa.links.items():
                # >>> ignora links inativos
                if not metrics.get("up", True):
                    continue
                graph[router_name].append((peer, metrics))
        
        # 2. Identifica todas as sub-redes únicas existentes na rede.
        all_remote_subnets = set()
        for lsa in self.lsdb.values():
            for link_info in lsa.links.values():
                all_remote_subnets.add(link_info["subnet"])
                
        for name, lsa in self.lsdb.items():
            print(name, lsa.to_json())

        # 3. Para cada sub-rede, calcula e instala a rota.
        for dest_subnet in all_remote_subnets:
            # Não precisa de uma rota para uma sub-rede à qual já está conectado.
            if dest_subnet in self.connected_subnets:
                continue
            
            # Encontra um roteador que está diretamente conectado à sub-rede de destino.
            # Este roteador será o "alvo" para o cálculo do caminho.
            print("dest_subnet: ", dest_subnet)
            dest_router_name = next((name for name, lsa in self.lsdb.items() if any(link['subnet'] == dest_subnet for link in lsa.links.values())), None)
            
            if not dest_router_name: continue

            # Por padrão, a intenção é apenas encontrar o caminho mais curto (menor custo).
            intent = Intent(self.name, dest_router_name)
            path = self.compute_path(intent, graph)
            print("intent-path", self.name, dest_router_name, path, graph)

            # Se um caminho foi encontrado, extrai o próximo salto (next hop).
            if path and len(path) > 1:
                next_hop_router = path[1] # O segundo elemento do caminho é o próximo roteador.
                if next_hop_router in self.links:
                    next_hop_ip = self.links[next_hop_router]['peer_ip']
                    print(f"[{self.name}] Rota para {dest_subnet}: próximo salto é {next_hop_router} ({next_hop_ip})")
                    
                    # 4. Monta e executa o comando `ip route` para atualizar o kernel.
                    # 'replace' funciona como 'add' se a rota não existe, ou a atualiza se já existir.
                    cmd = f"ip route replace {dest_subnet} via {next_hop_ip}"
                    try:
                        subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    except subprocess.CalledProcessError as e:
                        print(f"[{self.name}] Erro ao instalar a rota: {e.stderr.decode().strip()}")

    def compute_path(self, intent: Intent, graph: dict):
        """
        Calcula o caminho mais curto (menor custo) que atende às restrições de latência/largura de banda.
        A fila de prioridade armazena (custo, latência, nó, caminho_até_aqui).
        """
        # (custo total, latência total, nó, caminho)
        pq = [(0, 0, intent.src, [intent.src])]
        # Dicionário para rastrear o menor custo total para cada nó.
        min_costs = {intent.src: 0} 
        
        while pq:
            print("pq", pq)
            cost, latency, node, path = heapq.heappop(pq)
            
            # Se já encontramos um caminho para este nó com um custo menor, ignoramos este.
            # Isso é necessário porque podemos ter adicionado o nó à PQ com um custo maior antes.
            if cost > min_costs.get(node, float('inf')):
                continue
            
            if node == intent.dst: 
                return path
            
            # Explora os vizinhos do nó atual.
            for (nbr, metrics) in graph.get(node, []):
                n_cost, n_lat, n_band = metrics["cost"], metrics["latency"], metrics["bandwidth"]
                
                # A largura de banda mínima deve ser verificada no link
                if intent.min_bandwidth and n_band < intent.min_bandwidth: 
                    continue
                    
                new_cost = cost + n_cost
                new_latency = latency + n_lat
                
                # A latência máxima é uma restrição do caminho total
                if intent.max_latency and new_latency > intent.max_latency: 
                    continue
                
                # Se o novo custo for menor que o custo mínimo conhecido para o vizinho:
                if new_cost < min_costs.get(nbr, float('inf')):
                    min_costs[nbr] = new_cost # Atualiza o custo mínimo
                    # Adiciona o novo caminho à fila de prioridade
                    heapq.heappush(pq, (new_cost, new_latency, nbr, path + [nbr]))
            
        return None


    def run(self):
        """O loop principal do daemon do roteador."""
        print(f"[{self.name}] Daemon iniciado. Vizinhos: {list(self.peer_ports.keys())}")
        # Inicia a thread para receber LSAs em segundo plano.
        threading.Thread(target=self.receive_loop, daemon=True).start()
        
        while True:
            # Envia HELLOs
            
            self.send_hello()

            # Origina e inunda LSA
            self.lsdb[self.name] = self.originate_lsa()
            self.flood(self.lsdb[self.name])
            print(f"[{self.name}] Inundou LSA próprio. LSDB agora contém {len(self.lsdb)} entradas.")

            time.sleep(1)

            if self.lsdb:
                self.update_routing_table()

            time.sleep(5)


        # # Loop principal para publicitar LSAs e recalcular rotas periodicamente.
        # while True:
        #     # 1. Adiciona (ou atualiza) seu próprio LSA ao seu LSDB e o inunda na rede.
        #     #    A criação de um novo LSA atualiza o número de sequência (timestamp).
        #     self.lsdb[self.name] = self.originate_lsa()
        #     self.flood(self.lsdb[self.name])
            
        #     print(f"[{self.name}] Inundou LSA próprio. LSDB agora contém {len(self.lsdb)} entradas.")
            
        #     # 2. Aguarda um tempo para que os LSAs se propaguem pela rede.
        #     time.sleep(1) 
            
        #     # 3. Recalcula e atualiza a tabela de roteamento com base no LSDB atual.
        #     if self.lsdb:
        #         self.update_routing_table()
            
        #     # 4. Aguarda um intervalo maior antes de iniciar o próximo ciclo.
        #     time.sleep(5)

if __name__ == "__main__":
    # Configura o parser para ler os argumentos da linha de comando (passados pelo script Mininet).
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--links", nargs='+', action='append', help="Informação do link: peer_name peer_ip subnet cost latency bandwidth peer_port")
    args = parser.parse_args()

    # Cria e configura a instância do roteador.
    router = Router(args.name)
    if args.links:
        for link_info in args.links:
            router.add_link_info(*link_info)
    
    # Inicia a execução do daemon.
    router.run()