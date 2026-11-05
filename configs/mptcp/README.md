# Linux Multipath TCP

MPTCP is a transport feature in the Linux kernel. mptcpd manages path
endpoints; iproute2 exposes the relevant commands.

Inspect support on a target host with the upstream iproute2 tools. Example
endpoint configuration must be generated only after confirming the local
addresses, interfaces, kernel support and remote endpoint capability.

These settings are not applied by CI or the installer. MPTCP does not aggregate
arbitrary links unless the remote endpoint and network path support MPTCP.
