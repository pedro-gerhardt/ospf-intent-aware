#!/usr/bin/env python3
"""
Mininet testbed with 5 routers running a custom OSPF-like
Intent-aware link state protocol.
"""

from mininet.net import Mininet
from mininet.node import Controller, OVSBridge
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

import subprocess
import os

ROUTER_SCRIPT = "router_daemon.py"

def start_network():
    net = Mininet(controller=Controller, link=TCLink, switch=OVSBridge)

    routers = [net.addHost(f"r{i}") for i in range(1, 6)]

    net.addLink(routers[0], routers[1], delay="5ms", bw=100)
    net.addLink(routers[0], routers[2], delay="2ms", bw=10)
    net.addLink(routers[1], routers[2], delay="5ms", bw=50)
    net.addLink(routers[1], routers[4], delay="7ms", bw=80)
    net.addLink(routers[2], routers[3], delay="1ms", bw=200)
    net.addLink(routers[3], routers[4], delay="3ms", bw=150)

    net.start()

    procs = []
    for r in routers:
        neighbors = []
        for intf in r.intfList():
            if intf.link:
                other = intf.link.intf1 if intf.link.intf2.node == r else intf.link.intf2
                neighbors.append(other.node.name)

        print(r, neighbors)
        log_file = f"/tmp/{r.name}.log"
        cmd = f"python3 {ROUTER_SCRIPT} --name {r.name} --peers " \
            + " ".join(neighbors) \
            + f" > {log_file} 2>&1 &"
        p = r.popen(cmd, shell=True)
        procs.append(p)

    print("*** Network is ready. Use the CLI.")
    CLI(net)

    print("*** Stopping routing daemons")
    for p in procs:
        p.terminate()

    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    start_network()
