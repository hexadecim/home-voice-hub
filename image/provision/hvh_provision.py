#!/usr/bin/env python3
"""HVH-1 voice-assistant provisioning for a freshly installed Home Assistant OS.

Run from any computer on the same network AFTER the Home Assistant onboarding wizard
(create the owner account, then Profile > Security > Long-lived access tokens).

What it does (each step is idempotent and can be skipped):
  1. hostname                        (Supervisor /host/options)
  2. optional OS update to latest    (Supervisor /os/update; the device reboots)
  3. local speech services           Whisper (STT) and Piper (TTS) apps
  4. Assist Satellite app            (OHF-Voice/apps) using the on-board CM108B mic/speaker
  5. audio defaults                  CM108B USB codec as default input/output
  6. accepts Wyoming/ESPHome discoveries for the services above
  7. Anthropic (Claude) integration  as the conversation agent (needs your API key)
  8. Assist pipeline "HVH-1 Claude"  Whisper -> Claude -> Piper, set as preferred

Usage:
  pip install websockets
  python3 hvh_provision.py --url http://homeassistant.local:8123 --token <LLAT> \
          --anthropic-key sk-ant-... [--hostname hvh1] [--language en] [--update-os]
"""
import argparse, asyncio, json, sys, time, urllib.request, urllib.error

try:
    import websockets
except ImportError:
    sys.exit("pip install websockets")

OHF_REPO = "https://github.com/OHF-Voice/apps"

def log(*a): print("[hvh]", *a, flush=True)

class HA:
    def __init__(self, url, token):
        self.url = url.rstrip("/"); self.token = token; self.ws = None; self.id = 0

    # ---------------- REST
    def rest(self, method, path, body=None):
        req = urllib.request.Request(self.url + path, method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                t = r.read().decode() or "null"
                return json.loads(t)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path}: HTTP {e.code} {e.read().decode()[:300]}")

    # ---------------- WebSocket
    async def connect(self):
        wsurl = self.url.replace("http", "ws", 1) + "/api/websocket"
        self.ws = await websockets.connect(wsurl, max_size=64 * 1024 * 1024)
        await self.ws.recv()
        await self.ws.send(json.dumps({"type": "auth", "access_token": self.token}))
        msg = json.loads(await self.ws.recv())
        if msg.get("type") != "auth_ok": sys.exit(f"authentication failed: {msg}")
        log(f"connected to Home Assistant {msg.get('ha_version')}")

    async def call(self, mtype, **kw):
        self.id += 1; mid = self.id
        await self.ws.send(json.dumps({"id": mid, "type": mtype, **kw}))
        while True:
            msg = json.loads(await asyncio.wait_for(self.ws.recv(), 600))
            if msg.get("id") == mid and msg.get("type") == "result":
                if not msg.get("success"): raise RuntimeError(f"{mtype}: {msg.get('error')}")
                return msg.get("result")

    async def sv(self, endpoint, method="get", data=None, timeout=None):
        kw = {"endpoint": endpoint, "method": method}
        if data is not None: kw["data"] = data
        if timeout: kw["timeout"] = timeout
        return await self.call("supervisor/api", **kw)

# ------------------------------------------------------------------ steps
async def step_hostname(ha, name):
    info = await ha.sv("/host/info")
    if info.get("hostname") == name: log(f"hostname already {name}"); return
    await ha.sv("/host/options", "post", {"hostname": name}); log(f"hostname set to {name}")

async def step_os_update(ha):
    info = await ha.sv("/os/info")
    if not info.get("update_available"):
        log(f"HAOS {info.get('version')} is the latest"); return False
    log(f"updating HAOS {info.get('version')} -> {info.get('version_latest')} (device reboots)")
    try: await ha.sv("/os/update", "post", {}, timeout=1800)
    except Exception as e: log(f"update started ({e.__class__.__name__}); rerun this script when it is back")
    return True

async def addon_slug(ha, suffix):
    store = await ha.sv("/store/addons")
    addons = store if isinstance(store, list) else store.get("addons", [])
    for a in addons:
        if a["slug"] == suffix or a["slug"].endswith("_" + suffix): return a["slug"]
    return None

async def ensure_addon(ha, slug, options=None):
    info = await ha.sv(f"/addons/{slug}/info")
    if not info.get("version"):
        log(f"installing {slug} (can take several minutes)")
        await ha.sv(f"/store/addons/{slug}/install", "post", {}, timeout=1800)
        info = await ha.sv(f"/addons/{slug}/info")
    if options:
        merged = dict(info.get("options") or {}); merged.update(options)
        await ha.sv(f"/addons/{slug}/options", "post", {"options": merged})
    await ha.sv(f"/addons/{slug}/options", "post", {"boot": "auto", "watchdog": True})
    if info.get("state") != "started":
        await ha.sv(f"/addons/{slug}/start", "post", {}, timeout=600)
    log(f"{slug} running")

async def step_speech(ha, lang, voice):
    await ensure_addon(ha, "core_whisper", {"language": lang})
    await ensure_addon(ha, "core_piper", {"voice": voice})

async def step_satellite(ha, name):
    repos = await ha.sv("/store/repositories")
    if not any(r.get("source", "").rstrip("/") == OHF_REPO for r in (repos or [])):
        await ha.sv("/store/repositories", "post", {"repository": OHF_REPO}); log("added OHF Voice apps repository")
        await ha.sv("/store/reload", "post", {})
    slug = await addon_slug(ha, "assist_satellite")
    if not slug: raise RuntimeError("Assist Satellite app not found in the store")
    await ensure_addon(ha, slug, {"name": name})
    return slug

async def step_audio(ha):
    info = await ha.sv("/audio/info")
    audio = info.get("audio", {})
    def pick(lst):
        for d in lst:
            n = (d.get("name", "") + " " + d.get("description", "")).lower()
            if "c-media" in n or "cm108" in n or "usb_audio" in n or "usb audio" in n: return d["name"]
    i, o = pick(audio.get("input", [])), pick(audio.get("output", []))
    if i: await ha.sv("/audio/default/input", "post", {"name": i}); log(f"default input: {i}")
    if o: await ha.sv("/audio/default/output", "post", {"name": o}); log(f"default output: {o}")
    if not (i and o): log("CM108B codec not found in audio devices - check the USB hub (U7) and codec (U8)")

async def step_discoveries(ha, wait_s=90):
    want = {"wyoming", "esphome"}
    deadline = time.time() + wait_s; done = set()
    while time.time() < deadline:
        flows = await ha.call("config_entries/flow/progress")
        pending = [f for f in flows if f["handler"] in want and f["flow_id"] not in done]
        for f in pending:
            try:
                r = ha.rest("POST", f"/api/config/config_entries/flow/{f['flow_id']}", {})
                log(f"accepted {f['handler']} discovery -> {r.get('type')} {r.get('title', '')}")
            except Exception as e:
                log(f"could not accept {f['handler']} discovery: {e}")
            done.add(f["flow_id"])
        ents = await ha.call("entity_registry/list")
        have_stt = any(e["platform"] == "wyoming" and e["entity_id"].startswith("stt.") for e in ents)
        have_tts = any(e["platform"] == "wyoming" and e["entity_id"].startswith("tts.") for e in ents)
        have_sat = any(e["platform"] == "esphome" and e["entity_id"].startswith("assist_satellite.") for e in ents)
        if have_stt and have_tts and have_sat: return True
        await asyncio.sleep(5)
    log("not every discovery appeared yet (STT/TTS/satellite); check Settings > Devices & services")
    return False

async def step_anthropic(ha, key):
    entries = ha.rest("GET", "/api/config/config_entries/entry?domain=anthropic")
    if entries: log("Anthropic integration already configured"); return
    flow = ha.rest("POST", "/api/config/config_entries/flow", {"handler": "anthropic", "show_advanced_options": False})
    r = ha.rest("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", {"api_key": key})
    if r.get("type") != "create_entry": raise RuntimeError(f"Anthropic setup did not finish: {r.get('errors') or r}")
    log("Anthropic (Claude) integration added")

async def step_pipeline(ha, lang, voice):
    ents = await ha.call("entity_registry/list")
    pick = lambda plat, dom: next((e["entity_id"] for e in ents if e["platform"] == plat and e["entity_id"].startswith(dom + ".")), None)
    conv = pick("anthropic", "conversation"); stt = pick("wyoming", "stt"); tts = pick("wyoming", "tts")
    if not conv: raise RuntimeError("no Claude conversation entity yet")
    pipes = await ha.call("assist_pipeline/pipeline/list")
    pid = next((p["id"] for p in pipes["pipelines"] if p["name"] == "HVH-1 Claude"), None)
    body = dict(name="HVH-1 Claude", language=lang, conversation_engine=conv, conversation_language=lang,
                stt_engine=stt, stt_language=lang if stt else None, tts_engine=tts, tts_language=lang if tts else None,
                tts_voice=voice if tts else None, wake_word_entity=None, wake_word_id=None, prefer_local_intents=True)
    if pid: await ha.call("assist_pipeline/pipeline/update", pipeline_id=pid, **body)
    else: pid = (await ha.call("assist_pipeline/pipeline/create", **body))["id"]
    await ha.call("assist_pipeline/pipeline/set_preferred", pipeline_id=pid)
    log(f"pipeline 'HVH-1 Claude' ({stt} -> {conv} -> {tts}) is the preferred assistant")

async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://homeassistant.local:8123")
    ap.add_argument("--token", required=True, help="long-lived access token")
    ap.add_argument("--anthropic-key", help="Anthropic API key (console.anthropic.com)")
    ap.add_argument("--hostname")
    ap.add_argument("--name", default="HVH-1", help="satellite name")
    ap.add_argument("--language", default="en")
    ap.add_argument("--voice", default="en_US-lessac-medium", help="Piper voice")
    ap.add_argument("--update-os", action="store_true", help="update HAOS to the latest release first")
    ap.add_argument("--skip", default="", help="comma list: hostname,speech,satellite,audio,anthropic,pipeline")
    a = ap.parse_args()
    skip = set(filter(None, a.skip.split(",")))
    ha = HA(a.url, a.token); await ha.connect()
    if a.hostname and "hostname" not in skip: await step_hostname(ha, a.hostname)
    if a.update_os and await step_os_update(ha): return
    if "speech" not in skip: await step_speech(ha, a.language, a.voice)
    if "satellite" not in skip: await step_satellite(ha, a.name)
    if "audio" not in skip: await step_audio(ha)
    await step_discoveries(ha)
    if "anthropic" not in skip:
        if a.anthropic_key: await step_anthropic(ha, a.anthropic_key)
        else: log("no --anthropic-key: add Settings > Devices & services > Anthropic yourself")
    if "pipeline" not in skip:
        try: await step_pipeline(ha, a.language, a.voice)
        except Exception as e: log(f"pipeline step: {e}")
    log("done. Say 'Okay Nabu' to the HVH-1. Claude controls exposed entities via the Assist API;")
    log("review Settings > Voice assistants > Expose before giving it control of locks/alarms.")
    await ha.ws.close()

if __name__ == "__main__":
    asyncio.run(main())
