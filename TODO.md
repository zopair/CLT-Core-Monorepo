# OPENCONNECT roadmap

## Phase 0 — source and repository audit
- [x] Select an empty inactive repository and preserve main.
- [x] Create isolated branch openconnect/bootstrap.
- [x] Record upstream revisions and license restrictions.

## Phase 1 — architecture
- [x] Create source, config, scripts, tests and documentation layout.
- [x] Record architecture decision and license audit.
- [x] Add Linux installation and safe-apply scripts.

## Phase 2 — transport prototype
- [x] Reticulum identity persistence and inbound destination.
- [x] Encrypted link message echo.
- [x] RNS Resource file transfer.
- [x] LXMF delivery identity and callback.
- [x] Four-process localhost topology and replay helper.
- [ ] Confirm CI acceptance run.

## Phase 3 — physical media
- [x] Document Ethernet, Wi-Fi 802.11s, RNode, KISS and receive-only RTL-SDR/RDS.
- [ ] Validate Yggdrasil on physical nodes.
- [ ] Validate 802.11s/batman-adv on supported hardware.
- [ ] Validate RNode and KISS devices.
- [ ] Validate receive-only RDS with SDR.

## Phase 4 — disruption tolerance and multipath
- [x] Document ION-DTN/BPv7 separate-process boundary.
- [x] Document MPTCP/mptcpd path management.
- [ ] Validate ION BPv7 contact plan on real nodes.
- [ ] Validate MPTCP over two real IP paths.

## Phase 5 — security
- [x] Reticulum cryptographic identities and encrypted links.
- [x] Application replay rejection.
- [x] Signed configuration verification and atomic replacement.
- [x] systemd resource-control examples.
- [ ] Key rotation/revocation and independent security review.

## Phase 6 — delivery
- [ ] Confirm GitHub Actions success.
- [ ] Confirm GitHub Pages deployment.
- [ ] Perform physical hardware acceptance tests.

A task is complete only after its corresponding real test passes. File existence is not evidence of runtime support.
