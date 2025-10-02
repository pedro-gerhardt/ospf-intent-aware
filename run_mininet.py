#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Controller, OVSBridge
from mininet.link import TCLink  # TCLink permite adicionar parâmetros como delay e bandwidth
from mininet.cli import CLI
from mininet.log import setLogLevel
import socket, json, time, re, os

# Constantes e configurações
ROUTER_SCRIPT = "router_script.py" # Nome do arquivo do daemon
PORT_BASE = 10000                  # Porta base para o protocolo de roteamento
NUM_ROUTERS = 5                    # Usado para limpar logs antigos

def cleanup_logs():
    """Remove arquivos de log antigos de execuções anteriores."""
    print("*** Removendo arquivos de log antigos...")
    for i in range(1, NUM_ROUTERS + 1):
        log_file = f"/tmp/r{i}.log"
        try:
            os.remove(log_file)
        except FileNotFoundError:
            pass # Normal se o arquivo não existir

def start_network():
    """Cria e configura a topologia de rede no Mininet e executa os testes."""
    cleanup_logs()

    # Inicializa o Mininet com TCLink para controle de banda/latência
    net = Mininet(controller=Controller, link=TCLink, switch=OVSBridge)

    print("*** Criando roteadores e PCs")
    routers = [net.addHost(f"r{i}", ip=None) for i in range(1, NUM_ROUTERS+1)]
    r1, r2, r3, r4, r5 = routers
    pc1 = net.addHost('pc1', ip='172.16.1.10/24')
    pc5 = net.addHost('pc5', ip='172.16.5.10/24')

    # Configuração da topologia de links entre roteadores
    links_config = [
        (r1, r2, "10.0.12.0/24", "5ms", 20),
        (r1, r3, "10.0.13.0/24", "2ms", 40),
        (r2, r3, "10.0.23.0/24", "5ms", 50),
        (r2, r5, "10.0.25.0/24", "7ms", 80),
        (r3, r4, "10.0.34.0/24", "1ms", 200),
        (r4, r5, "10.0.45.0/24", "3ms", 150)
    ]

    # Adiciona os links ao Mininet com os IPs e parâmetros de QoS
    for src, dst, subnet, delay, bw in links_config:
        src_ip = subnet.replace('0/24', '1/24')
        dst_ip = subnet.replace('0/24', '2/24')
        net.addLink(src, dst, delay=delay, bw=bw, params1={'ip': src_ip}, params2={'ip': dst_ip})

    print("*** Criando links entre PCs e roteadores")
    net.addLink(pc1, r1, params1={'ip': '172.16.1.10/24'}, params2={'ip': '172.16.1.1/24'})
    net.addLink(pc5, r5, params1={'ip': '172.16.5.10/24'}, params2={'ip': '172.16.5.1/24'})

    net.start()
    start_time = time.time() # Marca o tempo de início para a métrica de convergência

    print("*** Configurando rota padrão nos PCs")
    pc1.cmd('ip route add default via 172.16.1.1')
    pc5.cmd('ip route add default via 172.16.5.1')

    print("*** Habilitando encaminhamento IP em todos os roteadores")
    for r in routers:
        r.cmd('sysctl -w net.ipv4.ip_forward=1')

    # --- Lógica para iniciar os daemons ---
    procs = []
    for r in routers:
        # Monta a linha de comando para iniciar o daemon em cada roteador
        cmd_args = [f"python3 -u {ROUTER_SCRIPT} --name {r.name}"]

        # Itera sobre as interfaces do roteador para descobrir seus links e vizinhos
        for intf in r.intfList():
            if intf.link:
                peer_node = intf.link.intf1.node if intf.link.intf2.node == r else intf.link.intf2.node
                
                # Se o vizinho for um roteador, passa a informação como '--links'
                if peer_node.name.startswith("r"):
                    peer_intf = intf.link.intf1 if intf.link.intf2.node == r else intf.link.intf2
                    peer_ip = peer_intf.ip
                    subnet = peer_ip.rsplit('.', 1)[0] + ".0/24"
                    
                    link_params = intf.link.intf1.params
                    delay_ms = int(link_params.get('delay', '0ms').replace('ms', ''))
                    bw_mbps = int(link_params.get('bw', 1000))
                    
                    peer_port = PORT_BASE + int(peer_node.name[1:])
                    cost = 1 # Custo fixo para todos os links

                    cmd_args.append(
                        f"--links {peer_node.name} {peer_ip} {subnet} {cost} {delay_ms} {bw_mbps} {peer_port}"
                    )
                # Se o vizinho for um PC, passa a informação como '--stub-network'
                elif peer_node.name.startswith("pc"):
                    subnet = intf.ip.rsplit('.', 1)[0] + ".0/24"
                    cost = 1
                    cmd_args.append(f"--stub-network {subnet} {cost}")

        log_file = f"/tmp/{r.name}.log"
        # Constrói o comando final, redirecionando a saída para um arquivo de log
        full_cmd = " ".join(cmd_args) + f" > {log_file} 2>&1 &"

        print(f"*** Iniciando daemon em {r.name}...")
        p = r.popen(full_cmd, shell=True)
        procs.append(p)

    # --- Execução sequencial dos testes de métricas ---
    convergence_metric(net, start_time)
    qos_metric(pc1, pc5)
    routing_table_metric(routers)
    path_analysis_metric(pc1, pc5)
    protocol_overhead_metric(routers, start_time)
    intent_test(pc1, pc5, net)
    reconvergence_metric(net, pc1, pc5)
    # ---------------------------------------------------

    print("\n*** Rede pronta. Daemons estão convergindo.")
    CLI(net) # Abre a interface de linha de comando do Mininet

    print("*** Parando os daemons de roteamento")
    for p in procs:
        p.terminate()
    net.stop()

# --- Funções de Coleta de Métricas ---

def convergence_metric(net, start_time):
    """Mede o tempo até que todos os nós da rede consigam se pingar."""
    print("\n*** Aguardando conectividade total da rede (pingall com fail-fast)...")
    for _ in range(180): # Timeout de 90 segundos
        if _ping_all_fail_fast(net):
            end_time = time.time()
            convergence_time = end_time - start_time
            # Formata a saída para ser facilmente parseada
            formatted_result = (
                f"\n"
                f"    Tipo: pingall fail-fast\n"
                f"    Tempo de Convergência: {convergence_time:.4f}sec\n"
            )
            print(f"--- METRIC_CONVERGENCE_START ---\n{formatted_result}\n--- METRIC_CONVERGENCE_END ---")
            break
        time.sleep(0.5)
    else:
        print("*** AVISO: Timeout! Conectividade total não foi estabelecida.")

def _ping_all_fail_fast(net):
    """Função auxiliar que pinga todos os pares e retorna False na primeira falha."""
    for source in net.hosts:
        for dest in net.hosts:
            if source == dest:
                continue
            # Ping com timeout de 1 segundo
            result = source.cmd(f'ping -c 1 -W 1 {dest.IP()}')
            if '1 received' not in result:
                return False # Falha, retorna imediatamente
    print("*** Conectividade total confirmada!")
    return True # Sucesso

def qos_metric(pc1, pc5):
    """Mede a qualidade de serviço (vazão) entre dois PCs usando iperf."""
    print("\n*** Realizando teste de desempenho (QoS) com iperf...")
    pc5.cmd('iperf -s &') # Inicia o servidor iperf
    time.sleep(1)
    # Executa o cliente iperf com saída em formato CSV (-y C) por 10 segundos (-t 10)
    iperf_result = pc1.cmd(f'iperf -c {pc5.IP()} -y C -t 10')
    parts = iperf_result.strip().split(',')
    interval = parts[6]
    bytes_transferred = int(parts[7])
    bandwidth_bps = float(parts[8])
    formatted_result = (
        f"\n"
        f"    Duração: {interval}sec\n"
        f"    Vazão: {bandwidth_bps / 1_000_000:.2f}Mbits/sec\n"
        f"    Dados Transferidos: {bytes_transferred / (1024*1024):.2f}MBytes\n"
    )
    print(f"--- METRIC_QOS_START ---\n{formatted_result}\n--- METRIC_QOS_END ---")
    pc5.cmd('kill %iperf') # Para o servidor iperf

def routing_table_metric(routers):
    """Coleta e exibe o tamanho da tabela de roteamento de cada roteador."""
    print("\n*** Coletando métricas de tabela de roteamento...")
    total_routes = 0
    routing_table_details = ""
    for r in routers:
        route_count_str = r.cmd('ip route | wc -l').strip()
        route_count = int(route_count_str)
        total_routes += route_count
        routing_table_details += f"    - Roteador {r.name}: {route_count} rotas\n"
    formatted_result = (
        f"\n"
        f"{routing_table_details}"
        f"    - Total na rede: {total_routes} rotas\n"
    )
    print(f"--- METRIC_ROUTING_TABLE_START ---\n{formatted_result}\n--- METRIC_ROUTING_TABLE_END ---")

def path_analysis_metric(pc1, pc5):
    """Executa um traceroute para visualizar o caminho entre dois hosts."""
    print("\n*** Analisando a rota de pc1 para pc5 com traceroute...")
    # O '-n' evita a resolução de nomes DNS, tornando o comando mais rápido
    traceroute_output = pc1.cmd(f'traceroute -n {pc5.IP()}')
    formatted_result = f"\n{traceroute_output}\n"
    print(f"--- METRIC_PATH_ANALYSIS_START ---\n{formatted_result}\n--- METRIC_PATH_ANALYSIS_END ---")

def protocol_overhead_metric(routers, start_time):
    """Analisa os logs para contar pacotes de controle (LSA, HELLO) gerados."""
    print("\n*** Analisando o overhead do protocolo (pacotes de controle)...")
    lsa_packets = 0
    hello_packets = 0
    for r in routers:
        log_file = f"/tmp/{r.name}.log"
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if "Gerando LSA" in line:
                        lsa_packets += 1
                    elif "Gerando HELLO" in line:
                        hello_packets += 1
        except FileNotFoundError:
            print(f"    - AVISO: Arquivo de log {log_file} não encontrado.")
    time_spent = time.time() - start_time
    formatted_result = (
        f"\n"
        f"      Tempo total: {time_spent:.2f}sec\n"
        f"      Total gerado de LSA: {lsa_packets}\n"
        f"      Total gerado de HELLO: {hello_packets}\n"
    )
    print(f"--- METRIC_PROTOCOL_OVERHEAD_START ---\n{formatted_result}\n--- METRIC_PROTOCOL_OVERHEAD_END ---")

def reconvergence_metric(net, pc1, pc5):
    """Mede o tempo de reconvergência após derrubar dinamicamente um link."""
    print("\n*** Medindo o tempo de reconvergência dinamicamente...")
    # 1. Descobre a rota atual
    traceroute_output = pc1.cmd(f'traceroute -n {pc5.IP()}')
    path_routers = get_path_routers(net, traceroute_output)
    
    if len(path_routers) < 2:
        print("    - AVISO: Não foi possível identificar um link para derrubar.")
        return

    # 2. Derruba o link entre os dois últimos roteadores do caminho
    r_a, r_b = path_routers[-2], path_routers[-1]
    print(f"    - Rota identificada: {' -> '.join([r.name for r in path_routers])}")
    print(f"    - Derrubando o link dinâmico ({r_a.name}-{r_b.name})...")
    net.configLinkStatus(r_a.name, r_b.name, 'down')
    start_time = time.time()

    # 3. Espera a conectividade ser restabelecida por uma rota alternativa
    for _ in range(120):
        result = pc1.cmd(f'ping -c 1 -W 1 {pc5.IP()}')
        if '1 received' in result:
            reconvergence_time = time.time() - start_time
            # 4. Verifica qual é a nova rota
            new_traceroute = pc1.cmd(f'traceroute -n {pc5.IP()}')
            new_path_routers = get_path_routers(net, new_traceroute)
            formatted_result = (
                f"\n"
                f"    Link derrubado: {r_a.name}-{r_b.name}\n"
                f"    Tempo para reconvergir: {reconvergence_time:.4f}sec\n"
                f"    Nova rota identificada: {' -> '.join([r.name for r in new_path_routers])}\n"
            )
            print(f"--- METRIC_RECONVERGENCE_START ---\n{formatted_result}\n--- METRIC_RECONVERGENCE_END ---")
            
            # 5. Restaura o link original e encerra
            net.configLinkStatus(r_a.name, r_b.name, 'up')
            print(f"    - Link {r_a.name}-{r_b.name} restaurado.")
            return
        time.sleep(0.5)

    print(f"    - AVISO: Timeout! Ping não foi restabelecido.")
    net.configLinkStatus(r_a.name, r_b.name, 'up')
    print(f"    - Link {r_a.name}-{r_b.name} restaurado.")

def get_path_routers(net, traceroute_output):
    """Parseia a saída do traceroute para extrair os nós roteadores do caminho."""
    ip_regex = re.compile(r'\s*(\d+\.\d+\.\d+\.\d+)\s*')
    lines = traceroute_output.strip().split('\n')
    router_ips = []
    for line in lines[1:]: # Ignora a primeira linha
        match = ip_regex.search(line)
        if match and match.group(1) != net.get('pc5').IP():
            router_ips.append(match.group(1))

    path_routers, seen_nodes = [], set()
    for ip in router_ips:
        node_found = None
        for node in net.hosts:
            if node.name.startswith('r'):
                for intf in node.intfList():
                    if intf.IP() == ip:
                        node_found = node
                        break
            if node_found:
                break
        if node_found and node_found not in seen_nodes:
            path_routers.append(node_found)
            seen_nodes.add(node_found)
    return path_routers

def send_intent(router, src, dst, max_latency=None, min_bandwidth=None):
    """Envia uma mensagem de intent para a porta de controle de um roteador."""
    msg = {"type": "INTENT", "src": src, "dst": dst,
           "max_latency": max_latency, "min_bandwidth": min_bandwidth}
    payload = json.dumps(msg).replace('"', '\\"')
    # Usa netcat (nc) para enviar a mensagem JSON via UDP
    router.cmd(f'echo "{payload}" | nc -u -w1 127.0.0.1 {20000 + int(router.name[1:])}')
    print(f"*** Intent enviada para {router.name}: {msg}")

def intent_test(pc1, pc5, net):
    """Executa uma sequência de testes para validar a funcionalidade intent-aware."""
    print(f"\n--- TEST_INTENT_AWARE_ROUTING_START ---")
    print("\n*** Iniciando teste de Intent Aware Routing")

    # Cenário 1: Rota natural, sem nenhuma intent.
    print(">>> Cenário 1: Sem restrição (rota natural)")
    print(pc1.cmd(f"traceroute -w 5 -n {pc5.IP()}"))

    # Cenário 2: Adiciona uma intent e verifica se a rota muda.
    print(">>> Cenário 2: Com restrição de latência (max_latency=50ms)")
    r1 = net.get("r1")
    send_intent(r1, "pc1", "pc5", min_bandwidth=30)
    time.sleep(15)  # Espera o roteador processar a intent e a rede convergir
    print(pc1.cmd(f"traceroute -w 5 -n {pc5.IP()}"))

    # Cenário 3: Derruba o link da rota da intent para forçar o fallback.
    print(">>> Cenário 3: Derrubando link r1–r3 (intent não satisfaz, volta pela rota antiga)")
    net.configLinkStatus("r1", "r3", "down")
    time.sleep(15)
    print(pc1.cmd(f"traceroute -w 5 -n {pc5.IP()}"))
    net.configLinkStatus("r1", "r3", "up") # Restaura o link
    print(f"Link r1-r3 restaurado.")
    print(f"--- TEST_INTENT_AWARE_ROUTING_END ---")
    time.sleep(15) # Espera a rede estabilizar novamente

if __name__ == "__main__":
    setLogLevel("info")
    start_network()