# OPENCONNECT

Decentralized, multi-medium connectivity infrastructure — research prototype.

OPENCONNECT links independent nodes over heterogeneous carriers, tests multi-hop forwarding, exchanges encrypted messages/files, and prepares for delayed delivery across intermittent links.

It is not an ISP or a method of creating global Internet access without a physical upstream route. Global Internet access requires a real gateway connected to another network.

## Implemented prototype
- Reticulum encrypted links and transport relays.
- LXMF delivery identity and signed inbound message callback.
- Four independent Reticulum processes over TCP loopback only.
- Encrypted link message echo and RNS Resource file transfer.
- LXMF direct message acceptance test.
- Application replay-window helper.
- Signed atomic configuration apply script.

## Boundaries
CI proves local TCP transport, not radio range, satellite access, physical mesh, or global Internet transit. LoRa is low-rate; FM/RDS is receive-only in this design. Yggdrasil, ION-DTN, MPTCP, OpenWrt 802.11s, KISS, RNode, RTL-SDR and Kubo are documented integration targets, not all activated in CI.

## Quick start
~~~sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python src/oc_node.py --help
python tests/integration_localhost.py
~~~

Original OPENCONNECT code is MIT licensed. Third-party dependencies retain their own licenses; see docs/LICENSING.md.
