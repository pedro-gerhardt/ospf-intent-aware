#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Controller, OVSBridge
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

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

    print("\n*** Rede pronta. Daemons estão convergindo.")
    print("*** Verifique /tmp/rX.log para a saída dos daemons.")
    print("*** Use a CLI. Tente 'pc1 ping pc2' após ~15 segundos.")
    CLI(net)

    print("*** Parando os daemons de roteamento")
    for p in procs:
        p.terminate()

    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    start_network()