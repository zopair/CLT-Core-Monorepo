# Yggdrasil IPv6 overlay

Yggdrasil is a separate IP overlay, not a replacement for Reticulum's
low-bandwidth multi-medium transport.

Generate a valid, unique cryptographic configuration with the upstream binary:

~~~sh
yggdrasil -genconf > yggdrasil.conf
~~~

Then configure only peers and listen endpoints that you control. Keep the
generated private key local and secret. Do not commit private keys.

OPENCONNECT does not launch Yggdrasil automatically and does not assume that
an overlay peer provides global Internet transit. Compare with cjdns before
choosing an IPv6 overlay implementation.

Upstream:
- https://github.com/yggdrasil-network/yggdrasil-go
- https://github.com/cjdelisle/cjdns
