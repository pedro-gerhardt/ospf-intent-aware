# OSPF Intent-Aware Routing

[English](#english) | [Português](#português)

---

<a name="english"></a>
## English

### Overview

This project implements an **intent-aware routing protocol** inspired by OSPF (Open Shortest Path First). The protocol uses Link-State Advertisements (LSAs) to build a complete network topology view and calculates optimal paths based on configurable constraints such as maximum latency and minimum bandwidth.

#### Key Features

- **Link-State Protocol**: Each router maintains a Link-State Database (LSDB) with the complete network topology
- **Intent-Based Routing**: Supports routing decisions based on QoS constraints (latency, bandwidth)
- **Dynamic Topology Discovery**: Routers detect neighbor failures through periodic health checks
- **Automatic Convergence**: The network automatically recalculates routes when topology changes occur
- **LSA Flooding**: Efficient propagation of routing information across the network

#### Architecture

The implementation consists of two main components:

1. **Router Daemon (`router_script.py`)**: Implements the routing logic, LSA generation/flooding, and kernel routing table updates
2. **Network Simulation (`run_mininet.py`)**: Creates a Mininet topology with 5 routers and various link characteristics

### How to Run

#### Prerequisites

- Docker installed on your system
- Privileged access (required for network namespace manipulation)

#### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ospf-intent-aware
   ```

2. **Build and run using the provided script**:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

   This script will:
   - Build the Docker image with Ubuntu 20.04 and Mininet
   - Start the container with necessary privileges
   - Launch the network simulation automatically

3. **Interact with the network**:
   
   Once the Mininet CLI appears, you can:
   
   ```bash
   # Wait ~15 seconds for network convergence
   
   # Test connectivity
   mininet> pingall
   
   # Trace route between routers
   mininet> r1 traceroute -n 10.0.45.2
   
   # View routing table
   mininet> r1 route -n
   
   # Check daemon logs
   mininet> r1 cat /tmp/r1.log
   
   # Simulate link failure
   mininet> link r2 r5 down
   
   # Wait a few seconds and check new routes
   mininet> r1 traceroute -n 10.0.45.2
   ```

4. **Exit the simulation**:
   ```bash
   mininet> exit
   ```

#### Manual Docker Build

If you prefer to build manually:

```bash
docker build -t ospf-intent-aware-img .
docker run -it --rm --privileged ospf-intent-aware-img
```

### Network Topology

```
    r1 -------- r2
    |  \        |  \
    |   \       |   \
    r3   \      |    r5
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

### Monitoring and Debugging

Each router daemon logs to `/tmp/rX.log` (where X is the router number). You can monitor these logs in real-time:

```bash
mininet> r1 tail -f /tmp/r1.log
```

---

<a name="português"></a>
## Português

### Visão Geral

Este projeto implementa um **protocolo de roteamento baseado em intenções** inspirado no OSPF (Open Shortest Path First). O protocolo utiliza Link-State Advertisements (LSAs) para construir uma visão completa da topologia da rede e calcular caminhos ótimos baseados em restrições configuráveis como latência máxima e largura de banda mínima.

#### Características Principais

- **Protocolo Link-State**: Cada roteador mantém um banco de dados de estado de enlaces (LSDB) com a topologia completa da rede
- **Roteamento Baseado em Intenções**: Suporta decisões de roteamento baseadas em restrições de QoS (latência, largura de banda)
- **Descoberta Dinâmica de Topologia**: Roteadores detectam falhas de vizinhos através de verificações periódicas
- **Convergência Automática**: A rede recalcula rotas automaticamente quando ocorrem mudanças na topologia
- **Inundação de LSAs**: Propagação eficiente de informações de roteamento pela rede

#### Arquitetura

A implementação consiste em dois componentes principais:

1. **Daemon do Roteador (`router_script.py`)**: Implementa a lógica de roteamento, geração/inundação de LSAs e atualização da tabela de roteamento do kernel
2. **Simulação da Rede (`run_mininet.py`)**: Cria uma topologia Mininet com 5 roteadores e várias características de enlaces

### Como Executar

#### Pré-requisitos

- Docker instalado no seu sistema
- Acesso privilegiado (necessário para manipulação de namespaces de rede)

#### Início Rápido

1. **Clone o repositório**:
   ```bash
   git clone <url-do-repositorio>
   cd ospf-intent-aware
   ```

2. **Compile e execute usando o script fornecido**:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

   Este script irá:
   - Construir a imagem Docker com Ubuntu 20.04 e Mininet
   - Iniciar o container com os privilégios necessários
   - Lançar a simulação da rede automaticamente

3. **Interaja com a rede**:
   
   Quando a CLI do Mininet aparecer, você pode:
   
   ```bash
   # Aguarde ~15 segundos para a convergência da rede
   
   # Teste a conectividade
   mininet> pingall
   
   # Trace a rota entre roteadores
   mininet> r1 traceroute -n 10.0.45.2
   
   # Visualize a tabela de roteamento
   mininet> r1 route -n
   
   # Verifique os logs do daemon
   mininet> r1 cat /tmp/r1.log
   
   # Simule uma falha de enlace
   mininet> link r2 r5 down
   
   # Aguarde alguns segundos e verifique as novas rotas
   mininet> r1 traceroute -n 10.0.45.2
   ```

4. **Saia da simulação**:
   ```bash
   mininet> exit
   ```

#### Build Manual do Docker

Se você preferir compilar manualmente:

```bash
docker build -t ospf-intent-aware-img .
docker run -it --rm --privileged ospf-intent-aware-img
```

### Topologia da Rede

```
    r1 -------- r2
    |  \        |  \
    |   \       |   \
    r3   \      |    r5
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

### Monitoramento e Debug

Cada daemon de roteador registra logs em `/tmp/rX.log` (onde X é o número do roteador). Você pode monitorar esses logs em tempo real:

```bash
mininet> r1 tail -f /tmp/r1.log
```

---

## Comparison with Standard OSPF

### English
*This section will contain detailed comparisons between our intent-aware implementation and standard OSPF protocol, including:*

- **Convergence time analysis**
- **Resource utilization metrics**
- **Path selection differences under various network conditions**
- **Scalability considerations**
- **Intent-based routing advantages and trade-offs**

*[Content to be added]*

### Português
*Esta seção conterá comparações detalhadas entre nossa implementação baseada em intenções e o protocolo OSPF padrão, incluindo:*

- **Análise do tempo de convergência**
- **Métricas de utilização de recursos**
- **Diferenças na seleção de caminhos sob várias condições de rede**
- **Considerações de escalabilidade**
- **Vantagens e trade-offs do roteamento baseado em intenções**

*[Conteúdo a ser adicionado]*

---

## Demo Videos

### English
*This section will contain links and descriptions of demonstration videos showing:*

- **Basic network convergence and routing**
- **Link failure recovery demonstration**
- **Intent-based path selection scenarios**
- **Performance under different network loads**

*[Videos to be added]*

### Português
*Esta seção conterá links e descrições de vídeos de demonstração mostrando:*

- **Convergência básica da rede e roteamento**
- **Demonstração de recuperação de falha de enlace**
- **Cenários de seleção de caminho baseado em intenções**
- **Performance sob diferentes cargas de rede**

*[Vídeos a serem adicionados]*

---

## License

*[Add your license information here]*

## Contributors

Gustavo Parcianello Cardona
Murilo Schuck
Pedro Gerhardt
