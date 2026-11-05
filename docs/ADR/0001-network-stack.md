# ADR-0001: Layered multi-medium network architecture

- Status: Accepted for prototype
- Date: 2026-11-05

## Decision

- Use Reticulum as the first tested multi-medium cryptographic transport.
- Use LXMF for signed message delivery over Reticulum.
- Evaluate Yggdrasil as an independent IPv6 overlay; compare cjdns but do not
  run both by default.
- Keep ION-DTN as a separate process and integrate through a documented local
  adapter boundary.
- Use MPTCP only for real IP paths and compatible endpoints.
- Treat FM/RDS as receive-only low-rate broadcast data, never as broadband or
  a bidirectional Internet path.

This preserves clear boundaries between transports, IP overlays, delayed
delivery, and global Internet gateways.
