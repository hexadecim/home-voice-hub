#!/usr/bin/env python3
"""Build the HVH-1 SD-card image.

Downloads the latest (or a pinned) Home Assistant OS release for the Raspberry Pi 5 /
Compute Module 5 (board "rpi5-64"), verifies it, and customises the FAT boot partition
for the HVH-1 carrier board:

  * config.txt   - HVH-1 section (USB current, debug UART, antenna, RTC charging, fan curve)
  * cmdline.txt  - serial console when DEBUG_UART=1
  * CONFIG/      - imported by HAOS at boot: NetworkManager Wi-Fi keyfile, udev rules,
                   SSH key, hostname marker

Output: hvh1-haos-<version>.img.xz (+ .sha256), a raw disk image for Raspberry Pi Imager,
balenaEtcher or `dd`.  It is an .img (raw block image), not an .iso: SD cards and the
CM5 boot ROM use raw images; ISO 9660 is only for optical media / PC installers.

Requirements: Python 3.8+, xz, mtools (mcopy/mtype/mmd).  macOS: `brew install xz mtools`.
Debian/Ubuntu: `sudo apt install xz-utils mtools`.  No root rights needed.

Usage:
  ./build_hvh_image.py -c hvh-image.conf               # latest stable HAOS
  ./build_hvh_image.py -c hvh-image.conf --haos-image haos_rpi5-64-18.5.img.xz   # offline
"""
import argparse, hashlib, json, lzma, os, re, shutil, struct, subprocess, sys, tempfile, urllib.request, uuid

BOARD = "rpi5-64"
GH_REPO = "home-assistant/operating-system"
UA = {"User-Agent": "hvh1-image-builder/1.0"}
HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ helpers
def log(*a): print("[hvh]", *a, flush=True)

def die(msg): print(f"[hvh] ERROR: {msg}", file=sys.stderr); sys.exit(1)

def read_conf(path):
    conf = {}
    if path:
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln: continue
            k, v = ln.split("=", 1)
            conf[k.strip()] = v.strip().strip('"').strip("'")
    return conf

def http_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)

def latest_version(channel):
    try:
        v = http_json(f"https://version.home-assistant.io/{channel}.json")["hassos"][BOARD]
        log(f"version.home-assistant.io ({channel}): HAOS {v}")
        return v
    except Exception as e:
        log(f"version.home-assistant.io unavailable ({e}); asking GitHub")
    if channel != "stable":
        die("non-stable channels need version.home-assistant.io; pin HAOS_VERSION instead")
    try:
        return http_json(f"https://api.github.com/repos/{GH_REPO}/releases/latest")["tag_name"]
    except Exception as e:
        log(f"GitHub API unavailable ({e}); reading git tags")
    out = subprocess.run(["git", "ls-remote", "--tags", f"https://github.com/{GH_REPO}"],
                         capture_output=True, text=True, check=True).stdout
    tags = sorted({m.group(1) for m in re.finditer(r"refs/tags/(\d+\.\d+)$", out, re.M)},
                  key=lambda t: tuple(int(x) for x in t.split(".")))
    if not tags: die("could not determine the latest HAOS release")
    return tags[-1]

def asset_digest(version, name):
    """sha256 published by GitHub for the release asset (None if not available)."""
    try:
        rel = http_json(f"https://api.github.com/repos/{GH_REPO}/releases/tags/{version}")
        for a in rel.get("assets", []):
            if a["name"] == name and (a.get("digest") or "").startswith("sha256:"):
                return a["digest"].split(":", 1)[1]
    except Exception:
        pass
    return None

def download(url, dst):
    log(f"downloading {url}")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r, open(dst + ".part", "wb") as f:
        total = int(r.headers.get("Content-Length") or 0); got = 0
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b); got += len(b)
            if total: print(f"\r  {got >> 20} / {total >> 20} MiB", end="", flush=True)
    print()
    os.replace(dst + ".part", dst)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def gpt_partitions(img):
    """[(index, name, first_lba, last_lba)] from the primary GPT."""
    with open(img, "rb") as f:
        f.seek(512); hdr = f.read(92)
        if hdr[:8] != b"EFI PART": die("image has no GPT")
        ent_lba, n, esz = struct.unpack_from("<QII", hdr, 72)
        f.seek(ent_lba * 512); tbl = f.read(n * esz)
    parts = []
    for i in range(n):
        e = tbl[i * esz:(i + 1) * esz]
        if e[:16] == b"\0" * 16: continue
        first, last = struct.unpack_from("<QQ", e, 32)
        name = e[56:128].decode("utf-16le").rstrip("\0")
        parts.append((i + 1, name, first, last))
    return parts

class Fat:
    """Tiny mtools wrapper for the boot partition inside the raw image."""
    def __init__(self, img, offset):
        self.spec = f"{img}@@{offset}"
        self.env = dict(os.environ, MTOOLS_SKIP_CHECK="1", MTOOLS_NO_VFAT="0")
    def run(self, *args, capture=False):
        r = subprocess.run(list(args[:1]) + ["-i", self.spec] + list(args[1:]), env=self.env,
                           capture_output=True, text=True)
        if r.returncode != 0: die(f"{' '.join(args)}: {r.stderr.strip()}")
        return r.stdout
    def read(self, path): return self.run("mtype", f"::{path}")
    def write(self, path, text):
        with tempfile.NamedTemporaryFile("w", delete=False, newline="\n") as t:
            t.write(text); tmp = t.name
        try: self.run("mcopy", "-o", tmp, f"::{path}")
        finally: os.unlink(tmp)
    def mkdir(self, path):
        r = subprocess.run(["mmd", "-i", self.spec, f"::{path}"], env=self.env, capture_output=True, text=True)
        if r.returncode != 0 and "exists" not in (r.stderr + r.stdout).lower(): die(r.stderr)

# ------------------------------------------------------------------ HVH-1 customisation
def config_section(conf):
    on = lambda k: conf.get(k, "0") in ("1", "yes", "true", "on")
    lines = ["", "# ---------------------------------------------------------------",
             "# HVH-1 carrier board (Raspberry Pi CM5).  Added by build_hvh_image.py.",
             "# HAOS keeps config.txt across OS updates, so these settings persist.",
             "[cm5]",
             "# Full USB port current (1.6 A total) even when the USB-C supply does not",
             "# announce 5 A; the HVH-1 USB ports are protected by TPS2553 switches.",
             "usb_max_current_enable=1",
             "# Fan on J7 (CM5 dedicated PWM/TACH): start at 55 C, full speed at 75 C",
             "dtparam=fan_temp0=55000,fan_temp0_hyst=5000,fan_temp0_speed=90",
             "dtparam=fan_temp1=62000,fan_temp1_hyst=5000,fan_temp1_speed=150",
             "dtparam=fan_temp2=68000,fan_temp2_hyst=5000,fan_temp2_speed=200",
             "dtparam=fan_temp3=75000,fan_temp3_hyst=5000,fan_temp3_speed=255"]
    lines += (["# Serial console on TP1 (TX) / TP2 (RX), 115200 8N1", "enable_uart=1"] if on("DEBUG_UART")
              else ["# Serial console on TP1/TP2: set DEBUG_UART=1 when building", "#enable_uart=1"])
    lines += (["# External antenna (CM5 U.FL -> SMA in the enclosure knock-out)", "dtparam=ant2"] if on("EXTERNAL_ANTENNA")
              else ["# External antenna (CM5 U.FL): set EXTERNAL_ANTENNA=1", "#dtparam=ant2"])
    uv = int(conf.get("RTC_CHARGE_UV") or 0)
    lines += ([f"# Trickle-charge the rechargeable RTC cell on J8", f"dtparam=rtc_bbat_vchg={uv}"] if uv
              else ["# Rechargeable RTC cell on J8: set RTC_CHARGE_UV (e.g. 3000000)", "#dtparam=rtc_bbat_vchg=3000000"])
    lines += ["[all]", ""]
    return "\n".join(lines)

def wifi_keyfile(conf):
    ssid, psk = conf.get("WIFI_SSID", ""), conf.get("WIFI_PSK", "")
    if not ssid: return None
    sec = (f"[wifi-security]\nauth-alg=open\nkey-mgmt=wpa-psk\npsk={psk}\n\n") if psk else ""
    return (f"[connection]\nid=hvh-wifi\nuuid={uuid.uuid5(uuid.NAMESPACE_DNS, 'hvh1-' + ssid)}\ntype=802-11-wireless\n\n"
            f"[802-11-wireless]\nmode=infrastructure\nssid={ssid}\n\n{sec}"
            f"[ipv4]\nmethod=auto\n\n[ipv6]\naddr-gen-mode=stable-privacy\nmethod=auto\n")

def customise(img, conf):
    parts = gpt_partitions(img)
    boot = next((p for p in parts if p[1] == "hassos-boot"), None)
    if not boot: die("hassos-boot partition not found - is this a HAOS image?")
    fat = Fat(img, boot[2] * 512)
    cfg = fat.read("/config.txt")
    if "os_prefix=slot-A/" not in cfg: die("unexpected config.txt (no RAUC slot prefix)")
    if "HVH-1 carrier board" not in cfg:
        cfg = cfg.rstrip("\n") + "\n" + config_section(conf)
        fat.write("/config.txt", cfg)
    cl = fat.read("/cmdline.txt").strip()
    cc = (conf.get("WIFI_COUNTRY") or "US").upper()
    if not re.fullmatch(r"[A-Z]{2}", cc): die("WIFI_COUNTRY must be a 2-letter code")
    cl = re.sub(r"\s*cfg80211\.ieee80211_regdom=\S+", "", cl) + f" cfg80211.ieee80211_regdom={cc}"
    if conf.get("DEBUG_UART", "0") in ("1", "yes", "true", "on") and "console=serial0" not in cl:
        cl = cl.replace("console=tty0", "console=serial0,115200 console=tty0")
    fat.write("/cmdline.txt", cl + "\n")
    # CONFIG folder (HAOS imports it on every boot, see /usr/sbin/haos-config)
    fat.mkdir("/CONFIG"); fat.mkdir("/CONFIG/udev")
    fat.write("/CONFIG/udev/99-hvh1.rules", open(os.path.join(HERE, "config", "udev", "99-hvh1.rules")).read())
    kf = wifi_keyfile(conf)
    if kf:
        fat.mkdir("/CONFIG/network"); fat.write("/CONFIG/network/hvh-wifi", kf)
        log(f"Wi-Fi keyfile for '{conf['WIFI_SSID']}' added")
    if conf.get("SSH_AUTHORIZED_KEY"):
        fat.write("/CONFIG/authorized_keys", conf["SSH_AUTHORIZED_KEY"].strip() + "\n")
    fat.write("/CONFIG/README-HVH1.txt",
              "HVH-1: HAOS imports this folder on every boot.\r\n"
              "network/ replaces ALL NetworkManager connections at each boot - delete the\r\n"
              "network folder after the first successful boot if you later change\r\n"
              "networking in the Home Assistant UI.\r\n"
              f"hostname requested: {conf.get('HOSTNAME', 'homeassistant')} (set by hvh_provision.py)\r\n"
              f"Wi-Fi country: {conf.get('WIFI_COUNTRY', 'US')} (kernel cmdline cfg80211.ieee80211_regdom)\r\n")
    return boot

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", "--config", default=os.path.join(HERE, "hvh-image.conf"))
    ap.add_argument("-o", "--outdir", default=".")
    ap.add_argument("--haos-image", help="use a local haos_rpi5-64-<ver>.img.xz instead of downloading")
    ap.add_argument("--no-compress", action="store_true", help="write a plain .img")
    a = ap.parse_args()
    conf = read_conf(a.config if os.path.exists(a.config) else None)
    for tool in ("mcopy", "mtype", "mmd"):
        if not shutil.which(tool): die(f"{tool} not found - install mtools")
    os.makedirs(a.outdir, exist_ok=True)
    if a.haos_image:
        src = a.haos_image
        m = re.search(r"haos_rpi5-64-([\w.]+)\.img\.xz$", os.path.basename(src))
        version = m.group(1) if m else "local"
    else:
        version = conf.get("HAOS_VERSION", "latest")
        if version == "latest": version = latest_version(conf.get("HAOS_CHANNEL", "stable"))
        name = f"haos_{BOARD}-{version}.img.xz"
        src = os.path.join(a.outdir, name)
        if not os.path.exists(src):
            download(f"https://github.com/{GH_REPO}/releases/download/{version}/{name}", src)
        want = asset_digest(version, name)
        got = sha256(src)
        if want and want != got: os.unlink(src); die(f"sha256 mismatch for {name}")
        log(f"sha256 {got} " + ("(matches GitHub release digest)" if want else "(no published digest; xz integrity check only)"))
    log(f"HAOS {version}: decompressing")
    img = os.path.join(a.outdir, f"hvh1-haos-{version}.img")
    with lzma.open(src) as fi, open(img, "wb") as fo: shutil.copyfileobj(fi, fo, 1 << 20)
    boot = customise(img, conf)
    log(f"boot partition customised (LBA {boot[2]}..{boot[3]})")
    out = img
    if not a.no_compress:
        log("compressing (xz -T0 -6)")
        subprocess.run(["xz", "-f", "-T0", "-6", img], check=True)
        out = img + ".xz"
    digest = sha256(out)
    open(out + ".sha256", "w").write(f"{digest}  {os.path.basename(out)}\n")
    log(f"done: {out}\n      sha256 {digest}\n      flash with Raspberry Pi Imager ('Use custom') or balenaEtcher")

if __name__ == "__main__":
    main()
