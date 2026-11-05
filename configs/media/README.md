# Media adapters and hardware boundaries

| Medium | Adapter strategy | Status |
|---|---|---|
| Ethernet | Reticulum TCP/UDP interfaces over a real IP link | CI loopback tested; physical NIC not tested |
| Wi-Fi 802.11s | Linux/OpenWrt mesh interface, then Reticulum AutoInterface or IP carrier | Documentation only |
| batman-adv | Optional L2 mesh routing under Linux | Documentation only |
| LoRa RNode | Reticulum RNodeInterface with RNode firmware and supported serial device | Hardware required |
| Packet Radio KISS | Reticulum KISSInterface connected to a TNC/serial KISS endpoint | Hardware required |
| RTL-SDR FM/RDS | RTL-SDR receive pipeline with GNU Radio and redsea | Receive-only telemetry; not a Reticulum uplink |
| Satellite telemetry | SatNOGS/SDR ground station | Telemetry reception only; not Internet access |

## RNode
Use https://github.com/markqvist/RNode_Firmware and the matching Reticulum
RNode interface. Frequency, bandwidth, spreading factor, coding rate and
transmit power are jurisdiction- and device-specific. No transmit frequency
or power is selected by this repository.

## Packet Radio KISS
Use a compatible TNC and the upstream Reticulum KISS interface. Serial port,
baud rate, radio configuration and permitted channel access must be set for
the actual device and local regulations.

## RTL-SDR / FM-RDS
The receive-only path is RTL-SDR -> GNU Radio or rtl_fm -> redsea -> validated
RDS metadata events. RDS has a low payload rate and is broadcast one-way. It
is suitable for small announcements or telemetry experiments, not interactive
browsing or a broadband uplink. This project does not transmit FM.

## Wi-Fi 802.11s
Create and validate the mesh interface with the device's supported driver and
OpenWrt/Linux tools first. Reticulum then uses an IP-capable carrier over that
interface. Do not assume every phone or Wi-Fi chipset supports concurrent
station and mesh/AP modes.
