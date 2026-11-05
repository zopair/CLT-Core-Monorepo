# Hardware compatibility checklist

| Hardware | Required capability | Current evidence |
|---|---|---|
| Linux host | Python 3.10+, TCP sockets | CI loopback test |
| OpenWrt router | Supported target, enough flash/RAM, compatible Wi-Fi driver | Not tested in CI |
| Wi-Fi mesh radio | Driver supports 802.11s and appropriate regulatory domain | Device-specific |
| RNode | Supported RNode board, serial/USB interface and compatible firmware | Not connected in CI |
| Packet radio | TNC exposing KISS over serial/TCP | Not connected in CI |
| RTL-SDR | Supported tuner and lawful reception frequency | Not connected in CI |
| Satellite terminal | Authorized bidirectional service and compatible terminal | Not connected in CI |

A smartphone's FM radio is usually a receiver path controlled by vendor
hardware/driver APIs. It must not be assumed to transmit. Android AP+STA and
mesh capabilities are also device/vendor dependent.

A satellite telemetry ground station is not an Internet service. A satellite
Internet gateway requires an authorized bidirectional service, a suitable
terminal and a real route to the Internet.
