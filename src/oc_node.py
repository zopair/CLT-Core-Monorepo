#!/usr/bin/env python3
"""OPENCONNECT Reticulum/LXMF node runtime using upstream APIs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

try:
    import RNS
    import LXMF
except ImportError as exc:
    raise SystemExit("Missing dependencies. Run pip install -r requirements.txt") from exc

from oc_protocol import ReplayWindow, make_envelope


def emit(path: str | None, event: dict) -> None:
    line = json.dumps(event, sort_keys=True)
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    print("OC_EVENT " + line, flush=True)


def load_or_create_identity(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        identity = RNS.Identity.from_file(str(path))
        if identity is None:
            raise RuntimeError("Could not load Reticulum identity: " + str(path))
        return identity
    identity = RNS.Identity()
    identity.to_file(str(path))
    return identity


class OpenConnectService:
    def __init__(self, config_dir: str, data_dir: str, event_log: str | None):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.event_log = event_log
        self.stop_event = threading.Event()
        self.peer_windows: dict[str, ReplayWindow] = {}
        self.latest_link = None
        self.reticulum = RNS.Reticulum(
            configdir=str(Path(config_dir).resolve()),
            loglevel=RNS.LOG_ERROR,
        )
        self.identity = load_or_create_identity(self.data_dir / "node.identity")
        self.destination = RNS.Destination(
            self.identity, RNS.Destination.IN, RNS.Destination.SINGLE,
            "openconnect", "node",
        )
        self.destination.set_link_established_callback(self._link_established)
        self.lxmf_router = LXMF.LXMRouter(
            identity=self.identity, storagepath=str(self.data_dir), autopeer=False,
        )
        self.lxmf_destination = self.lxmf_router.register_delivery_identity(
            self.identity, display_name="OPENCONNECT node",
        )
        self.lxmf_router.register_delivery_callback(self._lxmf_received)

    def _link_established(self, link) -> None:
        self.latest_link = link
        link.set_packet_callback(self._packet_received)
        link.set_resource_strategy(RNS.Link.ACCEPT_ALL)
        link.set_resource_concluded_callback(self._resource_received)
        emit(self.event_log, {"event": "link_established"})

    def _packet_received(self, message: bytes, packet) -> None:
        link = self.latest_link
        if link is None:
            return
        peer_key = getattr(link, "link_id", b"").hex() or "active-peer"
        window = self.peer_windows.setdefault(peer_key, ReplayWindow())
        try:
            envelope = json.loads(message.decode("utf-8"))
            accepted = window.accept(envelope.get("sequence"), envelope.get("nonce"))
            response = (
                {
                    "version": 1, "type": "ack",
                    "sequence": envelope["sequence"],
                    "nonce": envelope["nonce"],
                    "payload": envelope.get("payload"),
                }
                if accepted else {"version": 1, "type": "replay_rejected"}
            )
        except Exception:
            response = {"version": 1, "type": "invalid_envelope"}
        RNS.Packet(link, json.dumps(response).encode("utf-8")).send()

    def _resource_received(self, resource) -> None:
        if resource.status != RNS.Resource.COMPLETE:
            emit(self.event_log, {"event": "resource_failed", "status": int(resource.status)})
            return
        metadata = resource.metadata if isinstance(resource.metadata, dict) else {}
        filename = Path(str(metadata.get("filename", "received.bin"))).name
        if not filename or filename in {".", ".."}:
            filename = "received.bin"
        data = resource.data
        data.seek(0)
        content = data.read()
        target = self.data_dir / "received" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        emit(self.event_log, {
            "event": "file_received", "filename": filename, "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })

    def _lxmf_received(self, message) -> None:
        emit(self.event_log, {
            "event": "lxmf_received",
            "title": message.title_as_string(),
            "content": message.content_as_string(),
            "signature_validated": bool(message.signature_validated),
            "source_hash": message.source_hash.hex(),
        })

    def announce_loop(self, interval: float) -> None:
        while not self.stop_event.is_set():
            self.destination.announce()
            self.lxmf_router.announce(self.lxmf_destination.hash)
            self.stop_event.wait(interval)


def write_ready(path: str, destination_hash: str, lxmf_hash: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps({
        "destination_hash": destination_hash,
        "lxmf_hash": lxmf_hash,
        "ready_at": time.time(),
    }, indent=2), encoding="utf-8")
    os.replace(temp, target)


def serve(args) -> int:
    service = OpenConnectService(args.config_dir, args.data_dir, args.event_log)
    write_ready(args.ready_file, service.destination.hash.hex(), service.lxmf_destination.hash.hex())
    emit(args.event_log, {
        "event": "node_ready",
        "destination_hash": service.destination.hash.hex(),
        "lxmf_hash": service.lxmf_destination.hash.hex(),
    })
    threading.Thread(
        target=service.announce_loop, args=(args.announce_interval,), daemon=True,
    ).start()
    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        service.stop_event.set()
    return 0


def relay(args) -> int:
    reticulum = RNS.Reticulum(
        configdir=str(Path(args.config_dir).resolve()), loglevel=RNS.LOG_ERROR,
    )
    print("OC_RELAY_READY", flush=True)
    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        return 0
    finally:
        del reticulum


def wait_for_path(destination_hash: bytes, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if RNS.Transport.has_path(destination_hash):
            return True
        RNS.Transport.request_path(destination_hash)
        time.sleep(0.2)
    return RNS.Transport.has_path(destination_hash)


def probe(args) -> int:
    started = time.monotonic()
    reticulum = RNS.Reticulum(
        configdir=str(Path(args.config_dir).resolve()), loglevel=RNS.LOG_ERROR,
    )
    destination_hash = bytes.fromhex(args.destination)
    if len(destination_hash) != RNS.Reticulum.TRUNCATED_HASHLENGTH // 8:
        raise ValueError("Destination hash must be a 16-byte Reticulum hash")
    if not wait_for_path(destination_hash, args.timeout):
        raise TimeoutError("No Reticulum path discovered")
    identity = RNS.Identity.recall(destination_hash)
    if identity is None:
        raise RuntimeError("Destination identity could not be recalled")
    destination = RNS.Destination(
        identity, RNS.Destination.OUT, RNS.Destination.SINGLE, "openconnect", "node",
    )
    link = RNS.Link(destination)
    link_ready = threading.Event()
    message_ready = threading.Event()
    resource_ready = threading.Event()
    result: dict = {"message_received": False, "file_sent": False}
    file_handle = None

    def on_packet(message: bytes, packet) -> None:
        response = json.loads(message.decode("utf-8"))
        result["message_received"] = (
            response.get("type") == "ack" and response.get("payload") == args.message
        )
        result["reply"] = response
        message_ready.set()

    def on_resource(resource) -> None:
        result["file_sent"] = resource.status == RNS.Resource.COMPLETE
        result["resource_status"] = int(resource.status)
        if file_handle:
            file_handle.close()
        resource_ready.set()

    def on_established(established_link) -> None:
        nonlocal file_handle
        link_ready.set()
        envelope = make_envelope(args.message, 1)
        RNS.Packet(established_link, json.dumps(envelope).encode("utf-8")).send()
        file_handle = open(args.file, "rb")
        RNS.Resource(
            file_handle, established_link,
            metadata={"filename": Path(args.file).name},
            callback=on_resource, auto_compress=False,
        )

    link.set_packet_callback(on_packet)
    link.set_link_established_callback(on_established)
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if link_ready.is_set() and message_ready.is_set() and resource_ready.is_set():
            break
        time.sleep(0.05)
    if not (message_ready.is_set() and resource_ready.is_set()):
        raise TimeoutError("Message or file transfer did not complete")
    try:
        link.teardown()
    except Exception:
        pass

    lxmf_router = LXMF.LXMRouter(
        identity=RNS.Identity(), storagepath=str(Path(args.data_dir).resolve()), autopeer=False,
    )
    source = lxmf_router.register_delivery_identity(
        lxmf_router.identity, display_name="OPENCONNECT test node",
    )
    lxmf_hash = bytes.fromhex(args.lxmf_destination)
    if not wait_for_path(lxmf_hash, args.timeout):
        raise TimeoutError("No path to LXMF recipient")
    recipient_identity = RNS.Identity.recall(lxmf_hash)
    if recipient_identity is None:
        raise RuntimeError("LXMF recipient identity could not be recalled")
    lxmf_destination = RNS.Destination(
        recipient_identity, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery",
    )
    lxmf_message = LXMF.LXMessage(
        lxmf_destination, source, "OPENCONNECT LXMF direct delivery proof",
        "OPENCONNECT acceptance", desired_method=LXMF.LXMessage.DIRECT, include_ticket=True,
    )
    lxmf_router.handle_outbound(lxmf_message)
    lxmf_deadline = time.monotonic() + args.lxmf_timeout
    while time.monotonic() < lxmf_deadline:
        if lxmf_message.state in (
            LXMF.LXMessage.DELIVERED, LXMF.LXMessage.FAILED, LXMF.LXMessage.REJECTED,
        ):
            break
        time.sleep(0.2)
    result["lxmf_delivered"] = lxmf_message.state == LXMF.LXMessage.DELIVERED
    result["lxmf_state"] = int(lxmf_message.state)
    result["elapsed_seconds"] = round(time.monotonic() - started, 4)
    result["message_bytes"] = len(args.message.encode("utf-8"))
    result["file_bytes"] = Path(args.file).stat().st_size
    result["success"] = bool(
        result.get("message_received") and result.get("file_sent") and result.get("lxmf_delivered")
    )
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result["success"] else 2


def build_parser():
    parser = argparse.ArgumentParser(description="OPENCONNECT node runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    server = sub.add_parser("serve", help="Run an inbound Reticulum/LXMF node")
    server.add_argument("--config-dir", required=True)
    server.add_argument("--data-dir", required=True)
    server.add_argument("--ready-file", required=True)
    server.add_argument("--event-log")
    server.add_argument("--announce-interval", type=float, default=2.0)
    server.set_defaults(func=serve)

    relay_parser = sub.add_parser("relay", help="Run a Reticulum transport relay")
    relay_parser.add_argument("--config-dir", required=True)
    relay_parser.set_defaults(func=relay)

    client = sub.add_parser("probe", help="Send encrypted message, file and LXMF message")
    client.add_argument("--config-dir", required=True)
    client.add_argument("--data-dir", required=True)
    client.add_argument("--destination", required=True)
    client.add_argument("--lxmf-destination", required=True)
    client.add_argument("--message", default="OPENCONNECT loopback acceptance")
    client.add_argument("--file", required=True)
    client.add_argument("--timeout", type=float, default=20.0)
    client.add_argument("--lxmf-timeout", type=float, default=12.0)
    client.set_defaults(func=probe)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
