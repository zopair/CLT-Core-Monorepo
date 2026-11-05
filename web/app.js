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
  if(!response.ok)throw new Error("No CI-generated metrics are published.");
  const m=await response.json();
  text("status",m.status||"unknown");text("nodes",String(m.nodes??"—"));
  text("bytes",m.file_bytes?Number(m.file_bytes).toLocaleString()+" B":"—");
  text("elapsed",m.elapsed_seconds!=null?m.elapsed_seconds+" s":"—");
  text("evidence-log",JSON.stringify(m,null,2));
 }catch(e){text("status","NO DATA");text("evidence-log",e.message+" No measurements are fabricated.");}
}
function generate(){
 const profile=byId("profile").value,host=byId("host").value.trim()||"127.0.0.1";
 const port=Math.max(1024,Math.min(65535,Number(byId("port").value)||42100));
 let filename="reticulum.conf",body="";
 if(profile==="rnode")body="# RNode template; fill only device-supported and locally permitted values.\n[reticulum]\n  enable_transport = yes\n[interfaces]\n  [[RNode LoRa]]\n    type = RNodeInterface\n    enabled = no\n    port = /dev/ttyUSB0\n    frequency = <AUTHORIZED_FREQUENCY_HZ>\n    bandwidth = <SUPPORTED_BANDWIDTH_HZ>\n    txpower = <LEGAL_TX_POWER_DBM>\n";
 else if(profile==="kiss")body="# Packet radio KISS template\n[reticulum]\n  enable_transport = yes\n[interfaces]\n  [[KISS TNC]]\n    type = KISSInterface\n    enabled = no\n    port = /dev/ttyUSB0\n    speed = 9600\n";
 else if(profile==="sdr"){filename="sdr-rds-notes.txt";body="Receive-only chain: RTL-SDR -> GNU Radio/rtl_fm -> redsea -> validated RDS events. This is not a Reticulum transport or Internet uplink. No FM transmission is configured.\n";}
 else if(profile==="openwrt")body="# First configure and test 802.11s with the supported OpenWrt driver.\n[reticulum]\n  enable_transport = yes\n[interfaces]\n  [[Mesh Auto Interface]]\n    type = AutoInterface\n    enabled = yes\n    discovery_scope = link\n";
 else body="[reticulum]\n  enable_transport = yes\n  share_instance = no\n[logging]\n  loglevel = 4\n[interfaces]\n  [[Upstream TCP]]\n    type = TCPClientInterface\n    enabled = yes\n    target_host = "+host+"\n    target_port = "+port+"\n";
 generated={filename:filename,body:body};text("config",body);byId("download").disabled=false;
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