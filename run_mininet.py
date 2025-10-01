#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Controller, OVSBridge
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel
import time

ROUTER_SCRIPT = "router_script.py"
PORT_BASE = 10000

def start_network():
    """
    Cria e configura a topologia de rede no Mininet.
    """
    net = Mininet(controller=Controller, link=TCLink, switch=OVSBridge)

    routers = [net.addHost(f"r{i}", ip=None) for i in range(1, 6)]
    r1, r2, r3, r4, r5 = routers

    print("*** Adicionando PCs à topologia")
    pc1 = net.addHost('pc1', ip='172.16.1.10/24')
    pc2 = net.addHost('pc2', ip='172.16.5.10/24')

    links_config = [
        (r1, r2, "10.0.12.0/24", "5ms", 100),
        (r1, r3, "10.0.13.0/24", "2ms", 10),
        (r2, r3, "10.0.23.0/24", "5ms", 50),
        (r2, r5, "10.0.25.0/24", "7ms", 80),
        (r3, r4, "10.0.34.0/24", "1ms", 200),
        (r4, r5, "10.0.45.0/24", "3ms", 150)
    ]

    for src, dst, subnet, delay, bw in links_config:
        src_ip = subnet.replace('0/24', '1/24')
        dst_ip = subnet.replace('0/24', '2/24')
        net.addLink(src, dst, delay=delay, bw=bw, params1={'ip': src_ip}, params2={'ip': dst_ip})

    print("*** Criando links entre PCs e roteadores")
    net.addLink(pc1, r1, params1={'ip': '172.16.1.10/24'}, params2={'ip': '172.16.1.1/24'})
    net.addLink(pc2, r5, params1={'ip': '172.16.5.10/24'}, params2={'ip': '172.16.5.1/24'})

    net.start()

    start_time = time.time()
    print(f"[{start_time}] METRIC_NETWORK_START_TIME")

    print("*** Configurando rota padrão nos PCs")
    pc1.cmd('ip route add default via 172.16.1.1')
    pc2.cmd('ip route add default via 172.16.5.1')

    print("*** Habilitando encaminhamento IP em todos os roteadores")
    for r in routers:
        r.cmd('sysctl -w net.ipv4.ip_forward=1')

    procs = []
    for r in routers:
        cmd_args = [f"python3 {ROUTER_SCRIPT} --name {r.name}"]

        for intf in r.intfList():
            if intf.link:
                peer_node = intf.link.intf1.node if intf.link.intf2.node == r else intf.link.intf2.node
                # Se o vizinho for um roteador, adiciona como um peer OSPF
                if peer_node.name.startswith("r"):
                    # Encontra a interface do vizinho neste mesmo link.
                    peer_intf = intf.link.intf1 if intf.link.intf2.node == r else intf.link.intf2
                    # Obtém o IP exato da interface do vizinho.
                    peer_ip = peer_intf.ip
                    # Recria a string da sub-rede a partir do IP do vizinho.
                    subnet = peer_ip.rsplit('.', 1)[0] + ".0/24"
                    
                    # Obtém os parâmetros (delay, bw) do link.
                    link_params = intf.link.intf1.params
                    delay_ms = int(link_params.get('delay', '0ms').replace('ms', ''))
                    bw_mbps = int(link_params.get('bw', 1000))
                    
                    # Calcula a porta de escuta do daemon do vizinho.
                    peer_port = PORT_BASE + int(peer_node.name[1:])
                    
                    # O custo é usado pelo algoritmo de roteamento (ex: Dijkstra). Aqui, é fixo.
                    cost = 1

                    # Adiciona os detalhes do link como um argumento para o script do daemon.
                    # Cada link terá seu próprio argumento "--links".
                    cmd_args.append(
                        f"--links {peer_node.name} {peer_ip} {subnet} {cost} {delay_ms} {bw_mbps} {peer_port}"
                    )
                # Se o vizinho for um PC, informa o roteador sobre essa rede local
                elif peer_node.name.startswith("pc"):
                    subnet = intf.ip.rsplit('.', 1)[0] + ".0/24"
                    cost = 1 # Custo padrão para alcançar a rede local
                    cmd_args.append(f"--stub-network {subnet} {cost}")

        log_file = f"/tmp/{r.name}.log"
        full_cmd = " ".join(cmd_args) + f" > {log_file} 2>&1 &"

        print(f"*** Iniciando daemon em {r.name}...")
        p = r.popen(full_cmd, shell=True)
        procs.append(p)

    # --- Métricas ---
    convergence_metric(net, start_time)
    qos_metric(pc1, pc2)
    # ----------------

    print("\n*** Rede pronta. Daemons estão convergindo.")
    print("*** Verifique /tmp/rX.log para a saída dos daemons.")
    print("*** Use a CLI. Tente 'pc1 ping pc2' após ~15 segundos.")
    CLI(net)

    print("*** Parando os daemons de roteamento")
    for p in procs:
        p.terminate()

    net.stop()

def convergence_metric(net, start_time):
    print("\n*** Aguardando conectividade total da rede (pingall com fail-fast)...")

    for _ in range(120):
        if ping_all_fail_fast(net):
            end_time = time.time()
            convergence_time = end_time - start_time
            formatted_result = (
            f"\n"
            f"    Tipo: pingall fail-fast\n"
            f"    Tempo de Convergência: {convergence_time:.4f}sec\n"
            )
            print(f"--- METRIC_CONVERGENCE_START ---\n{formatted_result}\n--- METRIC_CONVERGENCE_END ---")
            break
        time.sleep(0.5) 
    else:
        print("*** AVISO: Timeout! Conectividade total (pingall) não foi estabelecida.")

def ping_all_fail_fast(net):
    """
    Executa um 'pingall', mas para e retorna False na primeira falha.
    Isso evita esperar o timeout de todos os outros pings.
    Retorna True somente se todos os pings forem bem-sucedidos.
    """
    for source in net.hosts:
        for dest in net.hosts:
            if source == dest:
                continue

            # Usa um ping com timeout curto para a verificação
            result = source.cmd(f'ping -c 1 -W 1 {dest.IP()}')

            # Se o ping falhar, informa qual foi e retorna False imediatamente
            if '1 received' not in result:
                return False

    # Se todos os pings do loop foram bem-sucedidos
    print("*** Conectividade total confirmada!")
    return True

def qos_metric(pc1, pc2):
    print("\n*** Realizando teste de desempenho (QoS) com iperf...")

    # Inicia o servidor iperf em pc2 em background
    pc2.cmd('iperf -s &')

    # Aguarda um instante para o servidor iniciar
    time.sleep(1)

    # Executa o cliente iperf em pc1 e captura a saída
    iperf_result = pc1.cmd(f'iperf -c {pc2.IP()} -y C -t 10')

    parts = iperf_result.strip().split(',')
    # Extrai as métricas do formato CSV do iperf para TCP
    interval = parts[6]
    bytes_transferred = int(parts[7])
    bandwidth_bps = float(parts[8])

    megabits_divisor = 1_000_000
    mebibytes_divisor = 1024 * 1024

    # Cria a string formatada para o log (sem jitter/loss)
    formatted_result = (
        f"\n"
        f"    Duração: {interval}sec\n"
        f"    Vazão: {bandwidth_bps / megabits_divisor:.2f} Mbits/sec\n"
        f"    Dados Transferidos: {bytes_transferred / mebibytes_divisor:.2f} MBytes\n"
    )
    print(f"--- METRIC_QOS_START ---\n{formatted_result}\n--- METRIC_QOS_END ---")
    
    # Para o servidor iperf em pc2
    pc2.cmd('kill %iperf')

if __name__ == "__main__":
    setLogLevel("info")
    start_network()
