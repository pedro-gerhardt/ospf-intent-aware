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
    mininet> pc1 ping pc2

    # Trace route between PCs
    mininet> pc1 traceroute pc2

    # View routing table on a router
    mininet> r1 route -n

    # Check daemon logs
    mininet> r1 cat /tmp/r1.log

    # Simulate a link failure
    mininet> link r2 r5 down

    # Wait a few seconds and check the new route
    mininet> pc1 traceroute pc2
    ```

4.  **Exit the simulation**:

    ```bash
    mininet> exit
    ```

### Network Topology

The topology consists of 5 routers and 2 PCs, with `pc1` connected to `r1` and `pc2` connected to `r5`.

```
    pc1 --- r1 -------- r2
            |  \        |  \
            |   \       |   \
            r3   \      |    r5 --- pc2
            |     \     |   /
            |      \    |  /
            r4 ---------+/
```

**Link Characteristics**:

  - r1-r2: 100 Mbps, 5ms delay
  - r1-r3: 10 Mbps, 2ms delay
  - r2-r3: 50 Mbps, 5ms delay
  - r2-r5: 80 Mbps, 7ms delay
  - r3-r4: 200 Mbps, 1ms delay
  - r4-r5: 150 Mbps, 3ms delay

### Metrics and Evaluation

The `run_mininet.py` script automatically collects and displays key performance metrics to evaluate the routing protocol. These metrics are essential for comparison and analysis.

  - **Convergence Time**: Measures the time until full network connectivity is achieved after startup.
  - **QoS (iperf)**: Tests throughput and total data transferred between `pc1` and `pc2`.
  - **Routing Table Size**: Reports the number of entries in each router's table, providing insight into memory overhead.
  - **Path Analysis (traceroute)**: Shows the actual path taken by packets between `pc1` and `pc2`.
  - **Protocol Overhead**: Counts the number of control packets (LSA and HELLO) generated to maintain routing tables.

### Comparison with Standard OSPF

*This section will contain detailed comparisons between our intent-aware implementation and a standard OSPF protocol, based on the automated metrics collected:*

  - **Convergence time analysis** after topology changes.
  - **Resource utilization metrics** (routing table size, protocol overhead).
  - **Path selection differences** under various intent-based constraints (e.g., low latency vs. high bandwidth).

*[Content to be added]*

### Demo Videos

*This section will contain links and descriptions of demonstration videos showing:*

  - **Basic network convergence** and routing between PCs.
  - **Link failure recovery demonstration**: showing how routes adapt automatically when a link is brought down.
  - **Intent-based path selection**: demonstrating how the network chooses a different path when a low-latency intent is specified, even if it's not the default shortest path.

*[Videos to be added]*

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
    mininet> pc1 ping pc2

    # Trace a rota entre os PCs
    mininet> pc1 traceroute pc2

    # Visualize a tabela de roteamento em um roteador
    mininet> r1 route -n

    # Verifique os logs do daemon
    mininet> r1 cat /tmp/r1.log

    # Simule uma falha de enlace
    mininet> link r2 r5 down

    # Aguarde alguns segundos e verifique a nova rota
    mininet> pc1 traceroute pc2
    ```

4.  **Saia da simulação**:

    ```bash
    mininet> exit
    ```

### Topologia da Rede

A topologia consiste em 5 roteadores e 2 PCs, com o `pc1` conectado ao `r1` e o `pc2` conectado ao `r5`.

```
    pc1 --- r1 -------- r2
            |  \        |  \
            |   \       |   \
            r3   \      |    r5 --- pc2
            |     \     |   /
            |      \    |  /
            r4 ---------+/
```

**Características dos Enlaces**:

  - r1-r2: 100 Mbps, 5ms de delay
  - r1-r3: 10 Mbps, 2ms de delay
  - r2-r3: 50 Mbps, 5ms de delay
  - r2-r5: 80 Mbps, 7ms de delay
  - r3-r4: 200 Mbps, 1ms de delay
  - r4-r5: 150 Mbps, 3ms de delay

### Métricas e Avaliação

O script `run_mininet.py` coleta e exibe automaticamente métricas de desempenho chave para avaliar o protocolo de roteamento. Essas métricas são fundamentais para a comparação e análise.

  - **Tempo de Convergência**: Mede o tempo necessário para que a rede atinja conectividade total após a inicialização.
  - **QoS (iperf)**: Testa a vazão e o total de dados transferidos entre o `pc1` e o `pc2`.
  - **Tamanho da Tabela de Roteamento**: Informa o número de entradas na tabela de cada roteador, dando uma ideia do consumo de memória.
  - **Análise de Caminho (traceroute)**: Mostra o caminho real que os pacotes percorrem entre o `pc1` e o `pc2`.
  - **Overhead do Protocolo**: Conta o número de pacotes de controle (LSA e HELLO) gerados para manter as tabelas de roteamento.

### Comparação com OSPF Padrão

*Esta seção conterá comparações detalhadas entre nossa implementação baseada em intenções e um protocolo OSPF padrão, com base nas métricas coletadas automaticamente:*

  - **Análise do tempo de convergência** após mudanças na topologia.
  - **Métricas de utilização de recursos** (tamanho da tabela de roteamento, overhead do protocolo).
  - **Diferenças na seleção de caminhos** sob várias restrições baseadas em intenção (ex: baixa latência vs. alta largura de banda).

*[Conteúdo a ser adicionado]*

### Vídeos de Demonstração

*Esta seção conterá links e descrições de vídeos de demonstração mostrando:*

  - **Convergência básica da rede** e roteamento entre PCs.
  - **Demonstração de recuperação de falha de enlace**: mostrando como as rotas se adaptam automaticamente quando um link é desativado.
  - **Seleção de caminho baseada em intenções**: demonstrando como a rede escolhe um caminho diferente quando uma intenção de baixa latência é especificada, mesmo que não seja o caminho mais curto padrão.

*[Vídeos a serem adicionados]*

-----

## License

*[Add your license information here]*

## Contributors

  - Gustavo Parcianello Cardona
  - Murilo Schuck
  - Pedro Gerhardt
