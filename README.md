-----

# OSPF Intent-Aware Routing

[English](#English) | [Português](#Português)

-----
## English

### Overview

This project implements an **intent-aware routing protocol** inspired by OSPF (Open Shortest Path First). The protocol uses Link-State Advertisements (LSAs) to build a complete network topology view and calculates optimal paths based on configurable constraints such as maximum latency and minimum bandwidth. The environment is simulated using Mininet, and the project includes automated scripts for performance evaluation.

#### Key Features

  - **Link-State Protocol**: Each router maintains a Link-State Database (LSDB) with the complete network topology.
  - **Intent-Based Routing**: Supports routing decisions based on QoS constraints (latency, bandwidth).
  - **Dynamic Topology Discovery**: Routers detect neighbor failures through periodic HELLO messages.
  - **Automatic Convergence**: The network automatically recalculates routes when topology changes occur.
  - **LSA Flooding**: Efficient propagation of routing information across the network.
  - **Support for Stub Networks**: Allows connecting end hosts (PCs) to the routing topology.

#### Architecture

The implementation consists of two main components:

1.  **Router Daemon (`router_script.py`)**: Implements the routing logic, LSA generation/flooding, and kernel routing table updates.
2.  **Network Simulation (`run_mininet.py`)**: Creates a Mininet topology with 5 routers, 2 PCs, and various link characteristics.

### How to Run

#### Prerequisites

  - Docker installed on your system.
  - Privileged access (required for network namespace manipulation).

#### Quick Start

1.  **Clone the repository**:

    ```bash
    git clone <repository-url>
    cd ospf-intent-aware
    ```

2.  **Build and run using the provided script**:

    ```bash
    chmod +x run.sh
    ./run.sh
    ```

    This script will:

      - Build the Docker image with Ubuntu 20.04 and Mininet.
      - Start the container with necessary privileges.
      - Launch the network simulation automatically.

3.  **Interact with the network**:

    Once the Mininet CLI appears, you can:

    ```bash
    # Wait ~15 seconds for network convergence

    # Test connectivity between all hosts, including PCs
    mininet> pingall

    # Test connectivity between PCs
    mininet> pc1 ping pc5

    # Trace route between PCs
    mininet> pc1 traceroute pc5

    # View routing table on a router
    mininet> r1 route -n

    # Check daemon logs
    mininet> r1 cat /tmp/r1.log

    # Simulate a link failure
    mininet> link r2 r5 down

    # Wait a few seconds and check the new route
    mininet> pc1 traceroute pc5
    ```

4.  **Exit the simulation**:

    ```bash
    mininet> exit
    ```

### Network Topology

The topology consists of 5 routers and 2 PCs, with `pc1` connected to `r1` and `pc5` connected to `r5`.

```
    pc1 --- r1 -------- r2
            |  \        |  \
            |   \       |   \
            r3   \      |    r5 --- pc5
            |     \     |   /
            |      \    |  /
            r4 ---------+/
```

**Link Characteristics**:

  - r1-r2: 20 Mbps, 5ms delay
  - r1-r3: 40 Mbps, 2ms delay
  - r2-r3: 50 Mbps, 5ms delay
  - r2-r5: 80 Mbps, 7ms delay
  - r3-r4: 200 Mbps, 1ms delay
  - r4-r5: 150 Mbps, 3ms delay

### Metrics and Evaluation

The `run_mininet.py` script automatically collects and displays key performance metrics to evaluate the routing protocol. These metrics are essential for comparison and analysis.

  - **Convergence Time**: Measures the time until full network connectivity is achieved after startup.
  - **QoS (iperf)**: Tests throughput and total data transferred between `pc1` and `pc5`.
  - **Routing Table Size**: Reports the number of entries in each router's table, providing insight into memory overhead.
  - **Path Analysis (traceroute)**: Shows the actual path taken by packets between `pc1` and `pc5`.
  - **Protocol Overhead**: Counts the number of control packets (LSA and HELLO) generated to maintain routing tables.
  - **Reconvergence Time**: Dynamic link failure recovery
  - **Intent-Aware Routing Test**:
    - Default shortest path
    - With max_latency or min_bandwidth constraints
    - Link failures with fallback path computation

### Injecting Intents

Intents can be sent to any router via UDP control socket:

```echo '{"type":"INTENT","src":"pc1","dst":"pc5","min_bandwidth":30}' \
  | nc -u -w1 127.0.0.1 20001
```

This forces r1 (listening on port 20001) to install a policy that prefers paths with at least 30 Mbps bandwidth between pc1 and pc5.

### Comparison with Standard OSPF

*This section will contain detailed comparisons between our intent-aware implementation and a standard OSPF protocol, based on the automated metrics collected:*

  - **Convergence time analysis** after topology changes.
  - **Resource utilization metrics** (routing table size, protocol overhead).
  - **Path selection differences** under various intent-based constraints (e.g., low latency vs. high bandwidth).

| Metric | Standard OSPF (Logs) | Intent-Aware OSPF (Video) | Analysis & Observations |
| :--- | :--- | :--- | :--- |
| **Initial Convergence** | `56.0394 seconds` | `22.7599 seconds` | The **Intent-Aware** implementation was **2.4x faster** in establishing initial network-wide connectivity. |
| **Dynamic Reconvergence** | `0.5362 seconds` | `5.0449 seconds` | **Standard OSPF was ~9.4x faster** in finding a new route after the `r2-r5` link failure. This may indicate that the additional logic for evaluating "intents" in your implementation adds overhead to the route recalculation process. |
| **QoS (iperf Throughput)** | `20.86 Mbits/sec` | `19.04 Mbits/sec` | Throughput was very similar in both scenarios, with a slight advantage for Standard OSPF. The difference is not significant. |
| **Routing Table** | `47 routes` | `40 routes` | Standard OSPF generated a slightly higher number of total routes in the network. |
| **Protocol Overhead (LSA)** | `12 LSA packets` | `20 LSA packets` | The **Intent-Aware** version generated **66% more LSA packets**, which is expected as it needs to propagate more state information (like latency and bandwidth) to make intelligent decisions. |
| **Default Route Latency** | `~25 ms` | `~24 ms` | The default route latency is **virtually identical** in both systems. This shows that, in this scenario, standard OSPF also selected an efficient path. The Intent-Aware advantage is not in the default route itself, but in its ability to change it dynamically. |
| **Alternate Route (Post-Failure)**| `r1 -> r3 -> r4 -> r5` | `r1 -> r3 -> r4 -> r5` | Both systems demonstrated correctness by identifying the same viable alternate route after the main link (`r2-r5`) failure. |
| **Intent-Based Route Selection** | Not applicable | Route switched to `~18 ms` | Only the Intent-Aware implementation was able to receive an intent (`max_latency=50ms`) and proactively switch the traffic flow to a route that met the requirement, **improving latency by 25%** compared to its own default route. |

### Demo Videos

  - **Basic network convergence**: routing between PCs.
  - **Link failure recovery demonstration**: showing how routes adapt automatically when a link is brought down.
  - **Intent-based path selection**: demonstrating how the network chooses a different path when a low-latency intent is specified, even if it's not the default shortest path.

The video is presented at the end of the README.md.

-----

\<a name="português"\>\</a\>

## Português

### Visão Geral

Este projeto implementa um **protocolo de roteamento baseado em intenções** inspirado no OSPF (Open Shortest Path First). O protocolo utiliza Link-State Advertisements (LSAs) para construir uma visão completa da topologia da rede e calcular caminhos ótimos com base em restrições configuráveis como latência máxima e largura de banda mínima. O ambiente é simulado com Mininet, e o projeto inclui scripts automatizados para avaliação de desempenho.

#### Características Principais

  - **Protocolo Link-State**: Cada roteador mantém um banco de dados de estado de enlaces (LSDB) com a topologia completa da rede.
  - **Roteamento Baseado em Intenções**: Suporta decisões de roteamento baseadas em restrições de QoS (latência, largura de banda).
  - **Descoberta Dinâmica de Topologia**: Roteadores detectam falhas de vizinhos através de mensagens HELLO periódicas.
  - **Convergência Automática**: A rede recalcula rotas automaticamente quando ocorrem mudanças na topologia.
  - **Inundação de LSAs**: Propagação eficiente de informações de roteamento pela rede.
  - **Suporte a Redes Stub**: Permite conectar hosts finais (PCs) à topologia de roteamento.

#### Arquitetura

A implementação consiste em dois componentes principais:

1.  **Daemon do Roteador (`router_script.py`)**: Implementa a lógica de roteamento, geração/inundação de LSAs e atualização da tabela de roteamento do kernel.
2.  **Simulação da Rede (`run_mininet.py`)**: Cria uma topologia Mininet com 5 roteadores, 2 PCs e várias características de enlaces.

### Como Executar

#### Pré-requisitos

  - Docker instalado no seu sistema.
  - Acesso privilegiado (necessário para manipulação de namespaces de rede).

#### Início Rápido

1.  **Clone o repositório**:

    ```bash
    git clone <url-do-repositorio>
    cd ospf-intent-aware
    ```

2.  **Compile e execute usando o script fornecido**:

    ```bash
    chmod +x run.sh
    ./run.sh
    ```

    Este script irá:

      - Construir a imagem Docker com Ubuntu 20.04 e Mininet.
      - Iniciar o contêiner com os privilégios necessários.
      - Lançar a simulação da rede automaticamente.

3.  **Interaja com a rede**:

    Quando a CLI do Mininet aparecer, você pode:

    ```bash
    # Aguarde ~15 segundos para a convergência da rede

    # Teste a conectividade entre todos os hosts, incluindo os PCs
    mininet> pingall

    # Teste a conectividade entre os PCs
    mininet> pc1 ping pc5

    # Trace a rota entre os PCs
    mininet> pc1 traceroute pc5

    # Visualize a tabela de roteamento em um roteador
    mininet> r1 route -n

    # Verifique os logs do daemon
    mininet> r1 cat /tmp/r1.log

    # Simule uma falha de enlace
    mininet> link r2 r5 down

    # Aguarde alguns segundos e verifique a nova rota
    mininet> pc1 traceroute pc5
    ```

4.  **Saia da simulação**:

    ```bash
    mininet> exit
    ```

### Topologia da Rede

A topologia consiste em 5 roteadores e 2 PCs, com o `pc1` conectado ao `r1` e o `pc5` conectado ao `r5`.

```
    pc1 --- r1 -------- r2
            |  \        |  \
            |   \       |   \
            r3   \      |    r5 --- pc5
            |     \     |   /
            |      \    |  /
            r4 ---------+/
```

**Características dos Enlaces**:

  - r1-r2: 20 Mbps, 5ms de delay
  - r1-r3: 40 Mbps, 2ms de delay
  - r2-r3: 50 Mbps, 5ms de delay
  - r2-r5: 80 Mbps, 7ms de delay
  - r3-r4: 200 Mbps, 1ms de delay
  - r4-r5: 150 Mbps, 3ms de delay

### Métricas e Avaliação

O script `run_mininet.py` coleta e exibe automaticamente métricas de desempenho chave para avaliar o protocolo de roteamento. Essas métricas são fundamentais para a comparação e análise.

  - **Tempo de Convergência**: Mede o tempo necessário para que a rede atinja conectividade total após a inicialização.
  - **QoS (iperf)**: Testa a vazão e o total de dados transferidos entre o `pc1` e o `pc5`.
  - **Tamanho da Tabela de Roteamento**: Informa o número de entradas na tabela de cada roteador, dando uma ideia do consumo de memória.
  - **Análise de Caminho (traceroute)**: Mostra o caminho real que os pacotes percorrem entre o `pc1` e o `pc5`.
  - **Overhead do Protocolo**: Conta o número de pacotes de controle (LSA e HELLO) gerados para manter as tabelas de roteamento.
  - **Teste de Roteamento Baseado em Intent**:
    - Roda menos custosa por padrão
    - Com restrições de latência e largura de banda
    - Falhas de conexões e cálculo de caminho por fallback

### Injetando Intents

As intents podem ser enviadas para qualquer roteador via soquete de controle UDP:

```bash
echo '{"type":"INTENT","src":"pc1","dst":"pc5","min_bandwidth":30}' \
  | nc -u -w1 127.0.0.1 20001
```

Isso força o `r1` (escutando na porta 20001) a instalar uma política que prefere caminhos com pelo menos 30 Mbps de largura de banda entre pc1 e pc5.
  
### Comparação com OSPF Padrão

*Esta seção conterá comparações detalhadas entre nossa implementação baseada em intenções e um protocolo OSPF padrão, com base nas métricas coletadas automaticamente:*

  - **Análise do tempo de convergência** após mudanças na topologia.
  - **Métricas de utilização de recursos** (tamanho da tabela de roteamento, overhead do protocolo).
  - **Diferenças na seleção de caminhos** sob várias restrições baseadas em intenção (ex: baixa latência vs. alta largura de banda).

| Métrica | OSPF Normal (Logs) | OSPF Intent-Aware (Vídeo) | Análise e Observações |
| :--- | :--- | :--- | :--- |
| **Convergência Inicial** | `56.0394 segundos` | `22.7599 segundos` | A implementação **Intent-Aware foi 2.4x mais rápida** para estabelecer a conectividade inicial em toda a rede. |
| **Reconvergência Dinâmica** | `0.5362 segundos` | `5.0449 segundos` | O **OSPF Normal foi ~9.4x mais rápido** para encontrar uma nova rota após a falha do link `r2-r5`. Isso pode indicar que a lógica adicional para avaliar as "intenções" na sua implementação adiciona um overhead ao processo de recálculo da rota. |
| **QoS (Vazão iperf)** | `20.86 Mbits/sec` | `19.04 Mbits/sec` | A vazão foi muito similar em ambos os cenários, com uma ligeira vantagem para o OSPF Normal. A diferença não é significativa. |
| **Tabela de Roteamento** | `47 rotas` | `40 rotas` | O OSPF Normal gerou um número ligeiramente maior de rotas totais na rede. |
| **Overhead de Protocolo (LSA)** | `12 pacotes LSA` | `20 pacotes LSA` | A versão **Intent-Aware gerou 66% mais pacotes LSA**, o que é esperado, já que precisa propagar mais informações de estado (como latência e banda) para tomar decisões inteligentes. |
| **Latência da Rota Padrão** | `~25 ms` | `~24 ms` | A latência da rota padrão é **praticamente idêntica** em ambos os sistemas. Isso mostra que, neste cenário, o OSPF padrão também selecionou um caminho eficiente. A vantagem do Intent-Aware não está na rota padrão, mas na sua capacidade de alterá-la dinamicamente. |
| **Rota Alternativa (Pós-Falha)** | `r1 -> r3 -> r4 -> r5` | `r1 -> r3 -> r4 -> r5` | Ambos os sistemas demonstraram corretude ao identificar a mesma rota alternativa viável após a falha do link principal (`r2-r5`). |
| **Seleção de Rota por Intenção** | Não aplicável | Rota alterada para `~18 ms` | Apenas a implementação Intent-Aware foi capaz de receber uma intenção (`max_latency=50ms`) e proativamente alterar o fluxo de tráfego para uma rota que atendesse ao requisito, **melhorando a latência em 25%** em relação à sua própria rota padrão. |

### Vídeos de Demonstração

*Esta seção conterá links e descrições de vídeos de demonstração mostrando:*

  - **Convergência básica da rede** e roteamento entre PCs.
  - **Demonstração de recuperação de falha de enlace**: mostrando como as rotas se adaptam automaticamente quando um link é desativado.
  - **Seleção de caminho baseada em intenções**: demonstrando como a rede escolhe um caminho diferente quando uma intenção de baixa latência é especificada, mesmo que não seja o caminho mais curto padrão.

https://github.com/user-attachments/assets/36c99780-64de-45db-b548-5b83739ae645

-----

## License

*[Add your license information here]*

## Contributors

  - Gustavo Parcianello Cardona
  - Murilo Schuck
  - Pedro Gerhardt
