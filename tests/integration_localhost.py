#!/usr/bin/env python3
"""Four-process Reticulum/LXMF acceptance test, bound strictly to 127.0.0.1."""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def write_config(directory: Path, transport: bool, listen_port: int | None,
                 upstream_port: int | None) -> None:
    lines = [
        "[reticulum]",
        f"  enable_transport = {'yes' if transport else 'no'}",
        "  share_instance = no",
        "  instance_control = no",
        "  panic_on_interface_error = no",
        "",
        "[logging]",
        "  loglevel = 7",
        "",
        "[interfaces]",
    ]
    if listen_port is not None:
        lines += [
            "  [[Downstream TCP]]",
            "    type = TCPServerInterface",
            "    enabled = yes",
            "    listen_ip = 127.0.0.1",
            f"    listen_port = {listen_port}",
            "",
        ]
    if upstream_port is not None:
        lines += [
            "  [[Upstream TCP]]",
            "    type = TCPClientInterface",
            "    enabled = yes",
            "    target_host = 127.0.0.1",
            f"    target_port = {upstream_port}",
            "",
        ]
    (directory / "config").write_text("\n".join(lines), encoding="utf-8")


def wait_ready(path: Path, process: subprocess.Popen, deadline: float) -> dict:
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        if process.poll() is not None:
            raise RuntimeError(f"node0 exited early with code {process.returncode}")
        time.sleep(0.1)
    raise TimeoutError("node0 did not publish its ready identity in time")


def wait_port(port: int, deadline: float, process: subprocess.Popen | None = None) -> None:
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"relay for 127.0.0.1:{port} exited with code {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"loopback listener 127.0.0.1:{port} did not open")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", default="web/data/metrics.json")
    args = parser.parse_args()
    started = time.monotonic()
    deadline = started + 37.0
    processes: list[subprocess.Popen] = []
    logs: list[Path] = []
    details: list[dict] = []
    result: dict = {}
    payload_bytes = 0
    success = False
    probe_started = False
    with tempfile.TemporaryDirectory(prefix="openconnect-acceptance-") as tmp:
        root = Path(tmp)
        try:
            # Four independent Reticulum instances form node0 <- node1 <- node2 <- node3.
            node_dirs = [root / f"node{i}" for i in range(4)]
            for d in node_dirs:
                d.mkdir()
            write_config(node_dirs[0], True, 42100, None)
            write_config(node_dirs[1], True, 42101, 42100)
            write_config(node_dirs[2], True, 42102, 42101)
            write_config(node_dirs[3], False, None, 42102)

            event_log = root / "node0-events.jsonl"
            ready_file = root / "node0-ready.json"
            node0_log = root / "node0.log"
            logs.append(node0_log)
            with node0_log.open("w", encoding="utf-8") as out:
                p0 = subprocess.Popen([
                    sys.executable, "src/oc_node.py", "serve",
                    "--config-dir", str(node_dirs[0]),
                    "--data-dir", str(node_dirs[0] / "data"),
                    "--ready-file", str(ready_file),
                    "--event-log", str(event_log),
                    "--announce-interval", "2",
                    "--announce-delay", "5",
                ], stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(p0)
            identity = wait_ready(ready_file, p0, min(deadline, time.monotonic() + 8))
            wait_port(42100, deadline)
            details.append({"event": "node_ready", "node": 0})

            for index, port in ((1, 42101), (2, 42102)):
                log = root / f"node{index}.log"
                logs.append(log)
                with log.open("w", encoding="utf-8") as out:
                    proc = subprocess.Popen([
                        sys.executable, "src/oc_node.py", "relay",
                        "--config-dir", str(node_dirs[index]),
                    ], stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
                processes.append(proc)
                wait_port(port, min(deadline, time.monotonic() + 7), proc)
                details.append({"event": "transport_relay_ready", "node": index, "port": port})
                time.sleep(0.35)

            # Let the two transport relays propagate node0's periodic announce
            # across the complete chain before the edge node requests its path.
            time.sleep(4.0)

            payload = root / "acceptance-payload.bin"
            payload.write_bytes(bytes(range(256)) * 512)
            payload_bytes = payload.stat().st_size
            probe_log = root / "node3-probe.log"
            logs.append(probe_log)
            with probe_log.open("w", encoding="utf-8") as out:
                probe_started = True
                probe = subprocess.run([
                    sys.executable, "src/oc_node.py", "probe",
                    "--config-dir", str(node_dirs[3]),
                    "--data-dir", str(node_dirs[3] / "data"),
                    "--destination", identity["destination_hash"],
                    "--lxmf-destination", identity["lxmf_hash"],
                    "--message", "OPENCONNECT four-node loopback acceptance",
                    "--file", str(payload),
                    "--timeout", "20",
                    "--lxmf-timeout", "8",
                ], stdout=out, stderr=subprocess.STDOUT,
                   timeout=max(1.0, deadline - time.monotonic()), check=False)
            probe_text = probe_log.read_text(encoding="utf-8", errors="replace")
            for line in reversed(probe_text.splitlines()):
                try:
                    candidate = json.loads(line)
                    if isinstance(candidate, dict) and "success" in candidate:
                        result = candidate
                        break
                except json.JSONDecodeError:
                    continue
            if probe.returncode != 0 or not result.get("success"):
                raise RuntimeError("probe did not confirm encrypted message, Resource file and LXMF delivery: " + probe_text[-1600:])
            if int(result.get("file_bytes", -1)) != payload_bytes:
                raise RuntimeError("transferred file byte count did not match generated payload")
            details.append({
                "event": "end_to_end_delivery",
                "message_received": result.get("message_received"),
                "file_sent": result.get("file_sent"),
                "lxmf_delivered": result.get("lxmf_delivered"),
                "file_bytes": payload_bytes,
            })
            success = len(processes) == 3 and bool(result.get("success"))
        except Exception as exc:
            details.append({"event": "acceptance_error", "error": str(exc)})
            for log_path in logs:
                if log_path.is_file():
                    details.append({
                        "event": "process_log_tail",
                        "source": log_path.name,
                        "tail": log_path.read_text(encoding="utf-8", errors="replace")[-2200:],
                    })
        finally:
            for proc in reversed(processes):
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                        proc.wait(timeout=1.5)
                    except Exception:
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
            elapsed = round(time.monotonic() - started, 4)
            metrics = {
                "status": "PASS" if success else "FAIL",
                "nodes": 4 if success or (len(processes) == 3 and probe_started) else len(processes),
                "file_bytes": int(result.get("file_bytes", 0)) if result.get("file_sent") else 0,
                "elapsed_seconds": elapsed,
                "test": "four independent Reticulum processes over 127.0.0.1",
                "checks": {
                    "encrypted_link_message": bool(result.get("message_received")),
                    "resource_file_transfer": bool(result.get("file_sent")),
                    "lxmf_direct_delivery": bool(result.get("lxmf_delivered")),
                },
                "details": details,
            }
            target = Path(args.metrics)
            target.parent.mkdir(parents=True, exist_ok=True)
            temp_file = target.with_suffix(target.suffix + ".tmp")
            temp_file.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temp_file, target)
            print(json.dumps(metrics, sort_keys=True), flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
