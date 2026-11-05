# OPENCONNECT architecture

The prototype separates physical carriers, Reticulum transport, LXMF messaging,
IP overlays, disruption-tolerant delivery, multipath IP transport and content
services. These are complementary layers, not a stack that must all be enabled
at once.

Reticulum is the first tested multi-medium transport. LXMF provides signed
message delivery. Yggdrasil is evaluated as an independent IPv6 overlay.
ION-DTN/BPv7 remains a separate process. Linux MPTCP applies only to real IP
paths and compatible endpoints.

The first acceptance topology is four independent Reticulum processes:
node0 listens on TCP 42100; node1 connects to node0 and listens on 42101;
node2 connects to node1 and listens on 42102; node3 connects to node2.
Every endpoint is bound to or targets 127.0.0.1. This proves local multi-hop
transport only, not radio range or global Internet transit.

A node becomes an Internet gateway only when it has a real upstream route and
an operator deliberately configures forwarding or a routed prefix. OPENCONNECT
does not silently share a participant's connection or change firewall rules.
