#!/usr/bin/env python3
"""Isolated, loopback-only multi-layer acceptance suite for OPENCONNECT."""
from __future__ import annotations

import concurrent.futures
import hashlib
import ipaddress
import json
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "web/data/metrics.json"
START = time.monotonic()
LIMIT = 48.0
LOCK = threading.Lock()


def run(cmd, *, env=None, timeout=6, check=True, text=True):
    return subprocess.run(
        cmd, cwd=ROOT, env=env, timeout=max(0.5, min(timeout, LIMIT - (time.monotonic() - START))),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=text, check=check,
    )


def wait_for(predicate, timeout=6, interval=0.15):
    end = min(time.monotonic() + timeout, START + LIMIT)
    while time.monotonic() < end:
        try:
            value = predicate()
            if value:
                return value
        except Exception:
            pass
        time.sleep(interval)
    raise TimeoutError("condition not reached before deadline")


def terminate_group(proc):
    if proc and proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=1.0)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def reticulum_base():
    target = Path(tempfile.gettempdir()) / ("openconnect-reticulum-base-" + str(os.getpid()) + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    p = run(
        ["python", "tests/integration_localhost.py", "--metrics", str(target)],
        timeout=39, check=False,
    )
    try:
        data = json.loads(target.read_text())
    except Exception:
        data = {"status": "FAIL", "details": [{"event": "missing_metrics", "output": p.stdout[-2500:]}]}
    try:
        target.unlink(missing_ok=True)
    except Exception:
        pass
    data["process_exit_code"] = p.returncode
    data["status"] = "PASS" if p.returncode == 0 and data.get("status") == "PASS" else "FAIL"
    return data


def reticulum_failover():
    procs = []
    logs = []
    details = []
    ok = False
    primary_result = {}
    after_result = {}
    root_tmp = Path(tempfile.mkdtemp(prefix="oc-failover-"))
    def cfg(name, transport, listens, upstreams):
        d = root_tmp / name
        d.mkdir()
        lines = [
            "[reticulum]", f"  enable_transport = {'yes' if transport else 'no'}",
            "  share_instance = no", "  instance_control = no",
            "  panic_on_interface_error = no", "", "[logging]", "  loglevel = 7", "", "[interfaces]",
        ]
        for n, port in enumerate(listens):
            lines += [
                f"  [[Downstream {n}]]", "    type = TCPServerInterface", "    enabled = yes",
                "    listen_ip = 127.0.0.1", f"    listen_port = {port}", "",
            ]
        for n, port in enumerate(upstreams):
            lines += [
                f"  [[Upstream {n}]]", "    type = TCPClientInterface", "    enabled = yes",
                "    target_host = 127.0.0.1", f"    target_port = {port}", "",
            ]
        (d / "config").write_text("\n".join(lines))
        return d
    def launch(args, logname):
        lp = root_tmp / logname
        logs.append(lp)
        out = lp.open("w")
        proc = subprocess.Popen(args, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        procs.append((proc, out, logname))
        return proc
    def probe(edge, identity, payload):
        f = root_tmp / payload
        f.write_bytes(os.urandom(32768))
        log = root_tmp / (payload + ".log")
        with log.open("w") as out:
            p = subprocess.run([
                "python", "src/oc_node.py", "probe",
                "--config-dir", str(edge), "--data-dir", str(edge / "data"),
                "--destination", identity["destination_hash"], "--lxmf-destination", identity["lxmf_hash"],
                "--message", "OPENCONNECT failover verification", "--file", str(f),
                "--timeout", "6", "--lxmf-timeout", "4", "--lxmf-path-timeout", "12",
            ], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
               timeout=max(1, min(22, START + LIMIT - time.monotonic())), check=False)
        parsed = {}
        for line in reversed(log.read_text(errors="replace").splitlines()):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "success" in obj:
                    parsed = obj
                    break
            except ValueError:
                pass
        return p.returncode == 0 and bool(parsed.get("success")), parsed, log.read_text(errors="replace")[-1200:]
    def probe_until_success(edge, identity, prefix):
        attempts = []
        last = (False, {}, "")
        for attempt in range(2):
            last = probe(edge, identity, f"{prefix}-{attempt + 1}.bin")
            attempts.append({"attempt": attempt + 1, "success": last[0],
                             "error": last[1].get("error")})
            if last[0]:
                break
            if attempt == 0:
                time.sleep(2.0)
        return (*last, attempts)
    try:
        root = cfg("root", True, [42110, 42114], [])
        primary = cfg("primary", True, [42111], [42110])
        backup = cfg("backup", True, [42115], [42114])
        middle = cfg("middle", True, [42112], [42111, 42115])
        edge = cfg("edge", False, [], [42112])
        ready = root_tmp / "root-ready.json"
        launch(["python", "src/oc_node.py", "serve", "--config-dir", str(root),
                "--data-dir", str(root / "data"), "--ready-file", str(ready),
                "--event-log", str(root_tmp / "root-events.jsonl"), "--announce-interval", "3", "--announce-delay", "5"], "root.log")
        identity = wait_for(lambda: json.loads(ready.read_text()) if ready.exists() else None, 7)
        wait_for(lambda: socket.create_connection(("127.0.0.1", 42110), .2).close() is None, 5)
        wait_for(lambda: socket.create_connection(("127.0.0.1", 42114), .2).close() is None, 5)
        for label, directory, port in (("primary", primary, 42111), ("middle", middle, 42112)):
            launch(["python", "src/oc_node.py", "relay", "--config-dir", str(directory)], label + ".log")
            wait_for(lambda p=port: (socket.create_connection(("127.0.0.1", p), .2).close() is None), 5)
        time.sleep(3.0)
        before, before_data, before_log, before_attempts = probe_until_success(edge, identity, "before-failover")
        primary_result = before_data
        details.append({"event": "primary_only_path_probe", "success": before, "attempts": before_attempts,
                        "file_bytes": before_data.get("file_bytes", 0),
                        "message_received": before_data.get("message_received", False),
                        "file_sent": before_data.get("file_sent", False),
                        "lxmf_delivered": before_data.get("lxmf_delivered", False)})
        if not before:
            raise RuntimeError("baseline probe over the primary relay failed: " + before_log)
        # Start the backup relay only after the primary path has carried real traffic.
        launch(["python", "src/oc_node.py", "relay", "--config-dir", str(backup)], "backup.log")
        wait_for(lambda: (socket.create_connection(("127.0.0.1", 42115), .2).close() is None), 5)
        def established_remote_port(port):
            try:
                rows = Path("/proc/net/tcp").read_text().splitlines()[1:]
                for row in rows:
                    fields = row.split()
                    if len(fields) > 3 and fields[3] == "01":
                        remote_port = int(fields[2].split(":")[1], 16)
                        if remote_port == port:
                            return True
            except Exception:
                return False
            return False
        wait_for(lambda: established_remote_port(42114) and established_remote_port(42115), 8)
        details.append({"event": "backup_tcp_links_established", "root_port": 42114, "middle_port": 42115})
        primary_proc = next(p for p, _, n in procs if n == "primary.log")
        terminate_group(primary_proc)
        time.sleep(2.0)
        after, after_data, after_log, after_attempts = probe_until_success(edge, identity, "after-failover")
        after_result = after_data
        details.append({"event": "probe_after_primary_relay_stopped", "success": after, "attempts": after_attempts,
                        "file_bytes": after_data.get("file_bytes", 0),
                        "message_received": after_data.get("message_received", False),
                        "file_sent": after_data.get("file_sent", False),
                        "lxmf_delivered": after_data.get("lxmf_delivered", False)})
        if not after:
            raise RuntimeError("delivery after primary relay loss failed: " + after_log)
        ok = True
    except Exception as exc:
        details.append({"event": "failover_error", "error": str(exc)})
        for log in logs:
            if log.exists():
                details.append({"event": "log_tail", "source": log.name, "tail": log.read_text(errors="replace")[-1200:]})
    finally:
        for proc, out, _ in reversed(procs):
            terminate_group(proc)
            try:
                out.close()
            except Exception:
                pass
        shutil.rmtree(root_tmp, ignore_errors=True)
    return {
        "failover_verified": ok,
        "primary_probe": primary_result,
        "after_failover_probe": after_result,
        "details": details,
    }


def reticulum_suite():
    # The first probe is the four-node chain. The backup relay is introduced only
    # after that path has carried encrypted data, a file and LXMF delivery.
    failover = reticulum_failover()
    primary = failover.get("primary_probe", {})
    checks = {
        "encrypted_link_message": bool(primary.get("message_received")),
        "resource_file_transfer": bool(primary.get("file_sent")),
        "lxmf_direct_delivery": bool(primary.get("lxmf_delivered")),
    }
    base = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "nodes": 4 if all(checks.values()) else 0,
        "file_bytes": int(primary.get("file_bytes", 0)) if checks["resource_file_transfer"] else 0,
        "elapsed_seconds": primary.get("elapsed_seconds"),
        "test": "four-node Reticulum chain with encrypted message, Resource file and LXMF",
        "checks": checks,
        "details": failover.get("details", []),
    }
    return {"reticulum_lxmf": base, "reticulum_failover": failover}


def yggdrasil_test():
    binary = Path(os.environ.get("YGGDRASIL_BIN", "yggdrasil"))
    ctl = Path(os.environ.get("YGGDRASILCTL_BIN", "yggdrasilctl"))
    if not binary.is_file() or not ctl.is_file():
        return {"yggdrasil_peered": False, "error": "Pinned upstream Yggdrasil binaries unavailable"}
    procs = []
    details = []
    with tempfile.TemporaryDirectory(prefix="oc-ygg-") as td:
        root = Path(td)
        def make(name, listen, peers, admin):
            generated = run([str(binary), "-genconf", "-json"], timeout=3).stdout
            conf = json.loads(generated)
            conf["IfName"] = "none"
            conf["Listen"] = [listen]
            conf["Peers"] = peers
            conf["AdminListen"] = "unix://" + str(admin)
            conf["MulticastInterfaces"] = []
            path = root / (name + ".json")
            path.write_text(json.dumps(conf))
            return path
        sock_a, sock_b = root / "ygg_a.sock", root / "ygg_b.sock"
        conf_a = make("a", "tcp://127.0.0.1:42201", ["tcp://127.0.0.1:42202"], sock_a)
        conf_b = make("b", "tcp://127.0.0.1:42202", ["tcp://127.0.0.1:42201"], sock_b)
        try:
            for conf, name in ((conf_a, "ygg-a.log"), (conf_b, "ygg-b.log")):
                log = (root / name).open("w")
                p = subprocess.Popen([str(binary), "-useconffile", str(conf)], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                procs.append((p, log))
            wait_for(lambda: sock_a.exists() and sock_b.exists(), 8)
            def admin(sock, command):
                return run([str(ctl), "-endpoint=unix://" + str(sock), "-json", command], timeout=3).stdout
            self_a = json.loads(admin(sock_a, "getSelf"))
            self_b = json.loads(admin(sock_b, "getSelf"))
            peers_a = wait_for(lambda: (lambda x: x if x.strip() and "127.0.0.1:422" in x else None)(admin(sock_a, "getPeers")), 7)
            peers_b = wait_for(lambda: (lambda x: x if x.strip() and "127.0.0.1:422" in x else None)(admin(sock_b, "getPeers")), 7)
            addr_a = self_a.get("address") or self_a.get("Address")
            addr_b = self_b.get("address") or self_b.get("Address")
            if not addr_a or not addr_b:
                raise RuntimeError("getSelf did not return both derived IPv6 addresses")
            ip_a, ip_b = ipaddress.ip_address(addr_a), ipaddress.ip_address(addr_b)
            if not (ip_a in ipaddress.ip_network("200::/7") and ip_b in ipaddress.ip_network("200::/7")):
                raise RuntimeError("Yggdrasil identity address is outside 200::/7")
            if not peers_a.strip() or not peers_b.strip():
                raise RuntimeError("getPeers returned no peer state")
            # Require the admin API to report an established encrypted peer on both nodes.
            peers_a_json, peers_b_json = json.loads(peers_a), json.loads(peers_b)
            if not any(peer.get("up") is True for peer in peers_a_json.get("peers", [])):
                raise RuntimeError("node A getPeers has no established peer")
            if not any(peer.get("up") is True for peer in peers_b_json.get("peers", [])):
                raise RuntimeError("node B getPeers has no established peer")
            combined = (peers_a + peers_b).lower()
            if "tcp://127.0.0.1:422" not in combined and "127.0.0.1:422" not in combined:
                raise RuntimeError("getPeers did not report the loopback TCP peers")
            details = [{"event": "ygg_self", "node": "a", "address": str(ip_a)},
                       {"event": "ygg_self", "node": "b", "address": str(ip_b)},
                       {"event": "getPeers", "node": "a", "output": peers_a[:1600]},
                       {"event": "getPeers", "node": "b", "output": peers_b[:1600]}]
            return {"yggdrasil_peered": True, "addresses": [str(ip_a), str(ip_b)], "details": details}
        except Exception as exc:
            return {"yggdrasil_peered": False, "error": str(exc), "details": details}
        finally:
            for p, log in reversed(procs):
                terminate_group(p)
                log.close()


def kubo_test():
    ipfs = Path(os.environ.get("IPFS_BIN", "ipfs"))
    if not ipfs.is_file():
        return {"ipfs_replicated": False, "error": "Pinned upstream Kubo binary unavailable"}
    daemons = []
    with tempfile.TemporaryDirectory(prefix="oc-kubo-") as td:
        root = Path(td)
        def cli(path, *args, timeout=5, check=True):
            env = os.environ.copy()
            env["IPFS_PATH"] = str(path)
            return run([str(ipfs), *args], env=env, timeout=timeout, check=check).stdout.strip()
        try:
            paths = [root / "a", root / "b"]
            ports = [42301, 42302]
            for path, port in zip(paths, ports):
                path.mkdir()
                env = os.environ.copy()
                env["IPFS_PATH"] = str(path)
                run([str(ipfs), "init", "--profile=test"], env=env, timeout=8)
                cli(path, "config", "Addresses.API", f"/ip4/127.0.0.1/tcp/{5001 + port - 42301}")
                cli(path, "config", "Addresses.Gateway", f"/ip4/127.0.0.1/tcp/{8080 + port - 42301}")
                cli(path, "config", "--json", "Addresses.Swarm", json.dumps([f"/ip4/127.0.0.1/tcp/{port}"]))
                cli(path, "config", "--json", "Bootstrap", "[]")
                cli(path, "config", "--json", "Discovery.MDNS.Enabled", "false")
                env["IPFS_PATH"] = str(path)
                log = (root / (path.name + ".log")).open("w")
                p = subprocess.Popen([str(ipfs), "daemon"], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                daemons.append((p, log))
            ids = []
            for path in paths:
                def ready(p=path):
                    try:
                        return json.loads(cli(p, "id", timeout=2))
                    except Exception:
                        return None
                ids.append(wait_for(ready, 10))
            peer_a, peer_b = ids[0]["ID"], ids[1]["ID"]
            cli(paths[1], "swarm", "connect", f"/ip4/127.0.0.1/tcp/42301/p2p/{peer_a}", timeout=6)
            payload = os.urandom(65536)
            source = root / "payload.bin"
            source.write_bytes(payload)
            cid = cli(paths[0], "add", "-Q", str(source), timeout=8)
            # Use binary-safe output for the content verification path.
            env_b = os.environ.copy()
            env_b["IPFS_PATH"] = str(paths[1])
            raw = subprocess.run([str(ipfs), "cat", cid], env=env_b, cwd=ROOT,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=True).stdout
            digest_a, digest_b = hashlib.sha256(payload).hexdigest(), hashlib.sha256(raw).hexdigest()
            if digest_a != digest_b or raw != payload:
                raise RuntimeError("CID retrieval content or SHA-256 did not match")
            return {"ipfs_replicated": True, "cid": cid, "file_bytes": len(raw),
                    "sha256": digest_b, "peer_ids": [peer_a, peer_b]}
        except Exception as exc:
            return {"ipfs_replicated": False, "error": str(exc)}
        finally:
            for p, log in reversed(daemons):
                terminate_group(p)
                log.close()


def mptcp_test():
    started = time.monotonic()
    result = {"mptcp_verified": False}
    server = client = None
    try:
        if not hasattr(socket, "IPPROTO_MPTCP"):
            socket.IPPROTO_MPTCP = 262
        if not Path("/proc/sys/net/mptcp/enabled").exists():
            raise RuntimeError("Kernel MPTCP sysctl is unavailable")
        enabled = Path("/proc/sys/net/mptcp/enabled").read_text().strip()
        if enabled != "1":
            raise RuntimeError("Kernel MPTCP is disabled; test did not change host sysctls")
        received = []
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_MPTCP)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(3)
        def accept():
            conn, _ = server.accept()
            with conn:
                conn.settimeout(3)
                received.append(conn.recv(4096))
                conn.sendall(b"OPENCONNECT-MPTCP-ACK")
        thread = threading.Thread(target=accept, daemon=True)
        thread.start()
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_MPTCP)
        client.settimeout(3)
        t0 = time.monotonic()
        client.connect(server.getsockname())
        client.sendall(b"OPENCONNECT-MPTCP-LOOPBACK-PAYLOAD")
        ack = client.recv(4096)
        thread.join(timeout=3)
        if not received or received[0] != b"OPENCONNECT-MPTCP-LOOPBACK-PAYLOAD" or ack != b"OPENCONNECT-MPTCP-ACK":
            raise RuntimeError("MPTCP socket payload exchange did not match")
        # TCP_IS_MPTCP is 43 on Linux; require the accepted socket to identify as MPTCP.
        is_mptcp = client.getsockopt(socket.IPPROTO_TCP, 43)
        if is_mptcp != 1:
            raise RuntimeError("Socket fell back to TCP; TCP_IS_MPTCP did not confirm MPTCP")
        result.update({"mptcp_verified": True, "rtt_ms": round((time.monotonic()-t0)*1000, 3),
                       "payload_bytes": len(received[0]), "kernel_enabled": True})
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        if client:
            client.close()
        if server:
            server.close()
    result["elapsed_seconds"] = round(time.monotonic() - started, 4)
    return result


def main():
    # Isolate Reticulum path discovery from the other protocol daemons first.
    results = {}
    try:
        results.update(reticulum_suite())
    except Exception as exc:
        results["reticulum_lxmf"] = {"status": "FAIL", "error": str(exc)}
        results["reticulum_failover"] = {"failover_verified": False, "error": str(exc)}

    other_tasks = {
        "yggdrasil": yggdrasil_test,
        "ipfs_kubo": kubo_test,
        "mptcp": mptcp_test,
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in other_tasks.items()}
        try:
            for future in concurrent.futures.as_completed(
                futures, timeout=max(1, LIMIT - (time.monotonic() - START))
            ):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    results[name] = {"error": str(exc)}
        except concurrent.futures.TimeoutError:
            pass
    for name in other_tasks:
        if name not in results:
            results[name] = {"error": "overall 48-second test deadline reached"}

    ret = results["reticulum_lxmf"]
    checks = {
        "reticulum_lxmf": ret.get("status") == "PASS" and all(ret.get("checks", {}).values()),
        "reticulum_failover": bool(results["reticulum_failover"].get("failover_verified")),
        "yggdrasil": bool(results["yggdrasil"].get("yggdrasil_peered")),
        "ipfs_kubo": bool(results["ipfs_kubo"].get("ipfs_replicated")),
        "mptcp": bool(results["mptcp"].get("mptcp_verified")),
    }
    elapsed = round(time.monotonic() - START, 4)
    metrics = {
        "schema_version": 2,
        "status": "PASS" if all(checks.values()) and elapsed <= 50 else "FAIL",
        "elapsed_seconds": elapsed,
        "loopback_only": True,
        "host_network_mutations": False,
        "checks": checks,
        "reticulum_lxmf": ret,
        "reticulum_failover": results["reticulum_failover"],
        "yggdrasil": results["yggdrasil"],
        "ipfs_kubo": results["ipfs_kubo"],
        "mptcp": results["mptcp"],
    }
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    tmp = METRICS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, METRICS)
    print(json.dumps(metrics, sort_keys=True), flush=True)
    return 0 if metrics["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
