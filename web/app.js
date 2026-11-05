(function(){
"use strict";
const byId=(id)=>document.getElementById(id);
let generated=null,lastSequence=-1,lastNonce="",lastAccepted=null;
function text(id,value){byId(id).textContent=value;}
function toBase64(bytes){let s="";new Uint8Array(bytes).forEach((b)=>s+=String.fromCharCode(b));return btoa(s);}
function fromBase64(value){const s=atob(value.trim());return Uint8Array.from(s,(c)=>c.charCodeAt(0));}
async function sha256(value){const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value));return Array.from(new Uint8Array(digest)).map((b)=>b.toString(16).padStart(2,"0")).join("");}
async function loadEvidence(){
 try{
  const response=await fetch("./data/metrics.json",{cache:"no-store"});
  if(!response.ok)throw new Error("No CI-generated multi-layer acceptance metrics are published.");
  const m=await response.json(),c=m.checks||{},r=m.reticulum_lxmf||{},y=m.yggdrasil||{},k=m.ipfs_kubo||{},p=m.mptcp||{},f=m.reticulum_failover||{};
  text("status",m.status||"FAIL");
  text("nodes",String(r.nodes??"—"));
  text("bytes",r.file_bytes!=null?Number(r.file_bytes).toLocaleString()+" B":"—");
  text("elapsed",m.elapsed_seconds!=null?m.elapsed_seconds+" s":"—");
  text("layer-reticulum",c.reticulum_lxmf?"PASS":"FAIL");
  text("detail-reticulum",c.reticulum_lxmf?"4-node encrypted message · file · LXMF":"One or more Reticulum/LXMF checks failed");
  text("layer-yggdrasil",c.yggdrasil?"PASS":"FAIL");
  text("detail-yggdrasil",Array.isArray(y.addresses)?y.addresses.join(" · "):(y.error||"No peer verification"));
  text("layer-ipfs",c.ipfs_kubo?"PASS":"FAIL");
  text("detail-ipfs",k.cid?("CID "+k.cid): (k.error||"No replication proof"));
  text("layer-mptcp",c.mptcp?"PASS":"FAIL");
  text("detail-mptcp",p.rtt_ms!=null?("RTT "+p.rtt_ms+" ms · "+(p.payload_bytes||0)+" B"): (p.error||"No MPTCP socket proof"));
  text("failover-status","Reticulum relay failover: "+(f.failover_verified?"PASS":"FAIL"));
  text("evidence-log",JSON.stringify(m,null,2));
 }catch(e){
  text("status","NO DATA");text("evidence-log",e.message+" No measurements are fabricated.");
  ["nodes","bytes","elapsed","layer-reticulum","layer-yggdrasil","layer-ipfs","layer-mptcp"].forEach((id)=>text(id,"—"));
  ["detail-reticulum","detail-yggdrasil","detail-ipfs","detail-mptcp"].forEach((id)=>text(id,"Awaiting CI evidence"));
  text("failover-status","Reticulum relay failover: awaiting evidence.");
 }
}
function generate(){
 const profile=byId("profile").value,rawHost=byId("host").value.trim()||"127.0.0.1";
 const host=/^[a-zA-Z0-9.-]+$/.test(rawHost)?rawHost:"127.0.0.1";
 const port=Math.max(1024,Math.min(65535,Number(byId("port").value)||42100));
 let filename="reticulum.conf",body="";
 if(profile==="rnode")body="# RNode template; fill only device-supported and locally permitted values.\n[reticulum]\n  enable_transport = yes\n[interfaces]\n  [[RNode LoRa]]\n    type = RNodeInterface\n    enabled = no\n    port = /dev/ttyUSB0\n    frequency = <AUTHORIZED_FREQUENCY_HZ>\n    bandwidth = <SUPPORTED_BANDWIDTH_HZ>\n    txpower = <LEGAL_TX_POWER_DBM>\n";
 else if(profile==="kiss")body="# Packet radio KISS template\n[reticulum]\n  enable_transport = yes\n[interfaces]\n  [[KISS TNC]]\n    type = KISSInterface\n    enabled = no\n    port = /dev/ttyUSB0\n    speed = 9600\n";
 else if(profile==="sdr"){filename="sdr-rds-notes.txt";body="Receive-only chain: RTL-SDR -> GNU Radio/rtl_fm -> redsea -> validated RDS events. This is not a Reticulum transport or Internet uplink. No FM transmission is configured.\n";}
 else if(profile==="openwrt")body="# First configure and test 802.11s with the supported OpenWrt driver.\n[reticulum]\n  enable_transport = yes\n[interfaces]\n  [[Mesh Auto Interface]]\n    type = AutoInterface\n    enabled = yes\n    discovery_scope = link\n";
 else if(profile==="yggdrasil"){
  filename="yggdrasil.conf";
  body="# Yggdrasil IPv6 overlay template. Yggdrasil assigns addresses in 200::/7.\n# Local multicast discovery is enabled; add trusted peers explicitly for non-LAN links.\nPeers: []\nListen: [\"tcp://0.0.0.0:0\"]\nAdminListen: none\nIfName: tun0\nMulticastInterfaces:\n  - Regex: .*\n    Beacon: true\n    Listen: true\n    Port: 0\nNodeInfoPrivacy: false\nAllowedPublicKeys: []\n";
 }else if(profile==="ion-dtn"){
  filename="ion_node.rc";
  body="# ION-DTN BPv7 node bootstrap command file (review against installed ION release).\n# Set a unique node number before running. This template binds local UDP convergence-layer endpoints only.\n# Storage and forwarding are persistent; size paths and quotas for the host.\n1 1 ''\ns\na scheme ipn 'ipnadmin'\na endpoint ipn:1.1 q\na induct udp 127.0.0.1:4556\na outduct udp 127.0.0.1:4556\nw 1\nq\n# Run only after reviewing ION version-specific BPv7 and UDPCL syntax.\n";
 }else if(profile==="mptcp"){
  filename="mptcp_gateway.sh";
  body="#!/usr/bin/env bash\n# Explicit operator-run MPTCP setup template. Review IFACE and LOCAL_ADDR first.\nset -euo pipefail\nIFACE=\"<NETWORK_INTERFACE>\"\nLOCAL_ADDR=\"<LOCAL_IP_ADDRESS>\"\ncommand -v ip >/dev/null\ncommand -v sysctl >/dev/null\ncommand -v systemctl >/dev/null\n[[ \"$IFACE\" != \"<NETWORK_INTERFACE>\" && \"$LOCAL_ADDR\" != \"<LOCAL_IP_ADDRESS>\" ]] || { echo 'Set IFACE and LOCAL_ADDR first' >&2; exit 2; }\nsudo sysctl -w net.mptcp.enabled=1\nsudo ip mptcp limits set subflows 4 add_addr_accepted 4\nsudo ip mptcp endpoint add \"$LOCAL_ADDR\" dev \"$IFACE\" subflow\n# mptcpd manages endpoint/path policy; confirm package and service name on this distro.\nsudo systemctl enable --now mptcpd\nsudo ip mptcp endpoint show\nsudo ip mptcp limits show\n";
 }else if(profile==="ipfs-kubo"){
  filename="ipfs_lowpower.sh";
  body="#!/usr/bin/env bash\n# Low-power Kubo bootstrap. Review limits and existing service ownership before running.\nset -euo pipefail\ncommand -v ipfs >/dev/null\ncommand -v systemctl >/dev/null\nif [[ ! -d \"$HOME/.ipfs\" ]]; then ipfs init; fi\nipfs config profile apply lowpower\nipfs config --json Discovery.MDNS.Enabled true\nSLICE=/etc/systemd/system/openconnect-ipfs.slice\nsudo install -d -m 0755 /etc/systemd/system\nsudo tee \"$SLICE\" >/dev/null <<'EOF'\n[Unit]\nDescription=OPENCONNECT low-power IPFS resource slice\n[Slice]\nCPUQuota=20%\nMemoryMax=512M\nTasksMax=128\nEOF\nsudo systemctl daemon-reload\n# Run Kubo inside the bounded slice; stop with: sudo systemctl stop openconnect-ipfs.service\nsudo systemd-run --unit=openconnect-ipfs --slice=openconnect-ipfs.slice --property=Restart=on-failure ipfs daemon\n";
 }else body="[reticulum]\n  enable_transport = yes\n  share_instance = no\n[logging]\n  loglevel = 4\n[interfaces]\n  [[Upstream TCP]]\n    type = TCPClientInterface\n    enabled = yes\n    target_host = "+host+"\n    target_port = "+port+"\n";
 generated={filename:filename,body:body};text("config",body);
 byId("download").disabled=false;
}
function download(){
 if(!generated)return;
 const url=URL.createObjectURL(new Blob([generated.body],{type:"text/plain;charset=utf-8"}));
 const a=document.createElement("a");a.href=url;a.download=generated.filename;a.click();URL.revokeObjectURL(url);
}
async function sign(){
 const pair=await crypto.subtle.generateKey({name:"Ed25519"},true,["sign","verify"]);
 const payload=byId("payload").value;
 const sig=await crypto.subtle.sign({name:"Ed25519"},pair.privateKey,new TextEncoder().encode(payload));
 const pub=await crypto.subtle.exportKey("raw",pair.publicKey);
 byId("pubkey").value=toBase64(pub);byId("signature").value=toBase64(sig);
 byId("sequence").value=String(Math.max(1,lastSequence+1));
 byId("nonce").value=(crypto.randomUUID?crypto.randomUUID():String(Date.now())+"-"+Math.random());
 text("crypto-result","Ephemeral Ed25519 signature created locally. No key was uploaded.");
}
async function verify(){
 const payload=byId("payload").value,seq=Number(byId("sequence").value),nonce=byId("nonce").value.trim();
 const key=await crypto.subtle.importKey("raw",fromBase64(byId("pubkey").value),{name:"Ed25519"},false,["verify"]);
 const valid=await crypto.subtle.verify({name:"Ed25519"},key,fromBase64(byId("signature").value),new TextEncoder().encode(payload));
 text("digest","SHA-256: "+await sha256(payload));
 if(!valid){text("crypto-result","SIGNATURE INVALID");return;}
 if(!Number.isSafeInteger(seq)||seq<0||!nonce){text("crypto-result","Invalid sequence or nonce.");return;}
 if(seq<=lastSequence||nonce===lastNonce){text("crypto-result","REPLAY REJECTED: duplicate or stale sequence/nonce.");return;}
 lastSequence=seq;lastNonce=nonce;lastAccepted={sequence:seq,nonce:nonce};
 text("crypto-result","SIGNATURE VALID — sequence and nonce accepted.");byId("replay").disabled=false;
}
function replay(){if(!lastAccepted)return;text("crypto-result",lastAccepted.sequence<=lastSequence&&lastAccepted.nonce===lastNonce?"REPLAY REJECTED — duplicate sequence and nonce.":"Replay guard check failed.");}
function failNode(failed){
 byId("fail").disabled=failed;byId("restore").disabled=!failed;
 text("route",failed?"What-if backup route: A → C → D. This is a visualization only.":"Primary route: A → B → C → D");
}
byId("generate").addEventListener("click",generate);
byId("download").addEventListener("click",download);
byId("sign").addEventListener("click",()=>sign().catch((e)=>text("crypto-result","WebCrypto Ed25519 unavailable: "+e.message)));
byId("verify").addEventListener("click",()=>verify().catch((e)=>text("crypto-result","Verification error: "+e.message)));
byId("replay").addEventListener("click",replay);
byId("fail").addEventListener("click",()=>failNode(true));
byId("restore").addEventListener("click",()=>failNode(false));
loadEvidence();
})();
