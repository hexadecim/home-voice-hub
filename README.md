# HVH-1 Home Voice Hub

HVH-1 is a single-board computer for home automation. It runs Home Assistant OS and works as a Claude-powered voice assistant: the on-board microphone hears the request, Home Assistant turns it into text, Claude (the Anthropic conversation agent) decides what to do and answers, and Piper speaks the answer through the on-board speaker amplifier.

This repository has everything needed to make one: schematic, 6-layer PCB, fabrication files with JLCPCB BOM and placement, a 3D-printed enclosure, and an SD-card image that installs the latest Home Assistant OS configured for this hardware.

> **Status: design complete, not yet prototyped.** Every footprint is checked against its part's pinout, and the schematic netlist matches `design.py` (132 parts, 103 nets, 0 errors). The board is fully routed and passes KiCad 7 DRC with **0 errors and 0 unconnected pads**. The only 4 warnings are silkscreen on the USB-C jack and the mute switch, which overhang the board edge on purpose. Every assembled part was in stock at LCSC when this was generated, except the MGM210P (see below). No board has been built or powered yet, so read the risk register before ordering more than a prototype batch.

## Contents

| Folder | What is in it |
|---|---|
| `kicad/` | KiCad 7 project: `hvh.kicad_sch` (7 sheets), the routed and filled `hvh.kicad_pcb`, symbol library and project rules. Open `hvh.kicad_pro` |
| `lib/hvh.pretty/` | Custom footprints (CM5 DF40 connectors, CM5 outline, MGM210P, RJ45, USB3-A, MEMS mic) |
| `fab/` | Gerber/drill zip (6 copper layers), JLCPCB BOM + CPL (111 placements, 46 line items), full BOM with sourcing and stock, board STEP, schematic PDF, top/bottom assembly PDFs, netlist |
| `enclosure/` | Base and lid as STL, 3MF and STEP, plus an assembly STEP |
| `image/` | SD-card image builder, configuration example, GitHub Actions workflow, Claude/voice provisioning script |
| `image/out/` | Pre-built `hvh1-haos-18.5.img.xz` (Ethernet first boot, no credentials inside) |
| `gen/` | Python generators that produce all of the above from `design.py` (single source of truth) |

## Hardware summary

| Function | Implementation |
|---|---|
| Compute | Raspberry Pi **Compute Module 5** (BCM2712, 4x Cortex-A76 2.4 GHz). Designed for CM5 Lite Wireless (CM5104000, 4 GB), but works with any CM5 (eMMC variants boot from eMMC instead of the microSD) |
| Wi-Fi / Bluetooth | On the CM5: 802.11ac **2.4 + 5 GHz**, Bluetooth 5.0 / BLE. PCB antenna, or the U.FL connector through the enclosure SMA knock-out |
| Zigbee / Thread | Silicon Labs **MGM210P** (EFR32MG21, +20 dBm, chip antenna), the same module as the Home Assistant Yellow, so it runs the official Yellow EmberZNet / OpenThread RCP firmware. Connects to the CM5 through a CP2102N USB-UART with hardware flow control |
| Power | **USB-C** input, 5 V. The CC lines go to the CM5, which negotiates 5 V / 5 A with the Raspberry Pi 27 W supply. Power button (SW1) uses the CM5 on/off/shutdown logic |
| USB-A | 1x **USB 3.0** (CM5 native, 5 Gbit/s) + 1x **USB 2.0** (hub port). Each port has a TPS2553 switch (about 1.0 A) and TPD4EUSB30 ESD protection |
| USB 2.0 hub | Terminus FE1.1s, 4 ports: USB-A, audio codec, Zigbee bridge, and one spare port on test points TP12/TP13 |
| Microphone | ZTS6216 analog MEMS mic (top port, 65 dB SNR). Feeds a CM108B USB audio codec, which shows up as a standard USB sound card (snd-usb-audio). **Mute** slide switch SW4 cuts the mic supply in hardware and lights the red mute LED |
| Speaker | CM108B line out to a PAM8302A 2.5 W class-D amp, then JST-PH J6 for a 4-8 ohm speaker (36 mm driver in the lid) |
| Ethernet | Gigabit (CM5 PHY) to a HanRun HR911130A MagJack with LEDs |
| Storage | **microSD** (Molex 104031-0811) on the CM5 SD interface, with RT9742 power switching for UHS-I |
| Other | Fan header (J7, CM5 PWM + tach), RTC backup cell (J8), rpiboot button (SW2), Zigbee bootloader button (SW3), 4 status LEDs, debug UART and SWD test points |
| PCB | 100 x 80 mm, **6 layers** (JLC06161H-3313, 1.6 mm), controlled impedance: USB 90 ohm diff, Ethernet 100 ohm diff |

### Layer stack

| Layer | Use |
|---|---|
| L1 F.Cu | Components, high-speed signals, GND pour |
| L2 In1 | Solid GND (reference for L1) |
| L3 In2 | Low-speed signals and USB 2.0, GND pour |
| L4 In3 | +5 V plane |
| L5 In4 | Solid GND (reference for L6) |
| L6 B.Cu | Signals, test points, GND pour |

Routing: 1,650 track segments and 316 vias. Most traces are on L1, with L6 and L3 used for crossings.

Design rules:
- 0.15 mm clearance; standard vias 0.6 / 0.3 mm.
- Three filled vias are inside pads: the GND pins of U5 (0.45 / 0.2 mm) and U8 (0.35 / 0.15 mm). JLC fills and caps vias on 6-layer boards (POFV) at no extra cost; check that it is selected.

Trace geometry for the controlled-impedance pairs is 0.16 / 0.24 mm (USB, 90 ohm) and 0.14 / 0.26 mm (Ethernet, 100 ohm) on the outer layers. Order with **impedance control** and let JLC adjust the widths for their exact stack.

## Ordering the board (JLCPCB)

1. Upload `fab/HVH-1_gerbers_drill.zip`. Choose 6 layers, 1.6 mm, stack-up **JLC06161H-3313**, impedance control on, ENIG recommended (fine-pitch DF40 pads).
2. Turn on PCB Assembly, top side (plus bottom if you want the test-point side populated; the bottom only has test points, so top-only is fine).
3. Upload `fab/HVH-1_BOM_JLCPCB.csv` and `fab/HVH-1_CPL_JLCPCB.csv`. Check the rotation preview, especially SOT-23, QFN and the USB/RJ45 connectors.
4. **MGM210PA32JIA2:** LCSC stock is low. Use JLC Global Sourcing, or consign the part from DigiKey (336-MGM210PA32JIA2-ND).
5. The **CM5 module is not soldered**: plug it into J10/J11 and fit four M2.5 screws with 1.5 mm spacers.
6. **Factory step:** program a Gecko bootloader and the Yellow EmberZNet firmware into the MGM210P through the SWD test points (TP7 SWCLK, TP8 SWDIO, TP9 RESET, TP10 SWO, TP11 3V3A, GND). After that, firmware updates go over USB from Home Assistant.

`fab/HVH-1_BOM_full.csv` lists the manufacturer, MPN, LCSC number, stock snapshot, price and alternate source for every line.

## Enclosure

Print `enclosure/hvh1_base.3mf` and `enclosure/hvh1_lid.3mf`. The lid is already flipped top-down for printing. Use PETG or ASA (the CM5 runs warm), 0.2 mm layers, 3 walls, no supports.

**Hardware needed**
- 4x M3 x 10 socket-head screws and 4x M3 heat-set inserts in the lid pillars. These clamp the PCB between the base and the lid.
- 4x M2.5 heat-set inserts in the base, plus 4x M2.5 x 8 screws and 1.5 mm spacers for the CM5.
- A 36 mm, 8 ohm, 1-2 W speaker (5 mm deep), pressed into the lid ring and wired to J6.
- 4x 2 mm acrylic rods, 18 mm long, as LED light pipes.
- A 0.8 mm foam ring gasket between the mic tube and the PCB, and an acoustic mesh sticker on the outside of the mic hole.
- 4x 10 mm rubber feet.

**Openings**
- Rear: USB-C, USB-A x2, RJ45.
- Front: microSD (with finger notch) and the mute slide (the wall is thinned around the lever).
- Top: power key (cantilever with plunger), 4 LED pipes, mic port, speaker grille, CM5 vents, and pinholes for rpiboot and the Zigbee bootloader.
- Sides: vents, kept away from the Zigbee antenna wall.
- Right wall: SMA knock-out for an external Wi-Fi antenna.

There is about 13 mm of space above the CM5 for a heatsink. The Raspberry Pi CM5 passive heatsink fits; a fan can use J7.

## Software: SD-card image

`image/build_hvh_image.py` downloads the newest Home Assistant OS for the Raspberry Pi 5 / CM5 (`rpi5-64`), checks it, and writes the HVH-1 settings into the boot partition:

- **config.txt**, in a `[cm5]` section that is kept across HAOS updates:
  - full USB current
  - fan curve for J7
  - optional serial console on TP1/TP2
  - optional external antenna
  - optional RTC cell charging
- **cmdline.txt**: Wi-Fi regulatory country (needed for 5 GHz), and the serial console when enabled.
- **CONFIG/**, which HAOS imports at boot:
  - optional Wi-Fi keyfile
  - udev rule that names the Zigbee radio `/dev/ttyHVHZigbee`
  - optional SSH key

```
cd image
cp hvh-image.conf.example hvh-image.conf      # edit Wi-Fi, country, options
python3 build_hvh_image.py -c hvh-image.conf   # needs: xz, mtools  (macOS: brew install xz mtools)
```

The output is `hvh1-haos-<version>.img.xz`. Flash it with Raspberry Pi Imager ("Use custom") or balenaEtcher. It is a raw disk image (`.img`), the format SD cards and the CM5 boot ROM use; an `.iso` is only for optical media and PC installers.

The GitHub workflow `image/build-image.workflow.yml` (copy it to `.github/workflows/` in your repository) rebuilds the image every week against the newest HAOS release. Wi-Fi credentials come from repository secrets, so keep that repository private, because the built image contains them. A running device also updates itself through the normal HAOS updater.

## Setting up the Claude voice assistant

1. Boot the device (Ethernet, or the Wi-Fi from your config). Open `http://homeassistant.local:8123` and finish onboarding.
2. Create a long-lived access token: Profile > Security.
3. Get an API key from the Anthropic Console (console.anthropic.com).
4. Run the provisioning script from any computer on the network:

```
pip install websockets
python3 image/provision/hvh_provision.py --url http://homeassistant.local:8123 \
    --token <token> --anthropic-key <key> --hostname hvh1 --update-os
```

The `--update-os` run installs the newest HAOS and reboots the device. Run the script again without that flag. It then:

1. Installs and starts **Whisper** (speech to text) and **Piper** (text to speech).
2. Installs the **Assist Satellite** app (OHF-Voice/apps), which listens to the on-board mic for the wake word "Okay Nabu".
3. Makes the CM108B codec the default microphone and speaker.
4. Accepts the Wyoming and ESPHome discoveries.
5. Adds the **Anthropic** integration.
6. Creates the "HVH-1 Claude" Assist pipeline (Whisper > Claude > Piper) and sets it as preferred.

Claude can then answer questions and control the devices you expose to Assist. Check Settings > Voice assistants > Expose before giving it locks or alarms. Zigbee: Home Assistant offers to set up ZHA (or Thread/Matter) on the discovered radio; pick the "HVH-1 Zigbee" serial port.

## Risk register (read before production)

| # | Risk | Mitigation |
|---|---|---|
| 1 | No prototype built yet; the layout comes from a custom grid autorouter (`gen/router.py`), not hand routing | Order 5 boards first. Do bring-up in this order: power, CM5 boot, USB, Ethernet, audio, Zigbee. Get an independent EE review of the schematic PDF and layout |
| 2 | Impedance of the USB3 / Ethernet pairs depends on the fab stack-up | Order with impedance control and give the fab the target values (90 / 100 ohm diff) |
| 3 | HR911130A LED pin polarity taken from the EasyEDA model | Check LED orientation on the first boards; swapping only changes LED colour/behaviour |
| 4 | PCM12 slide switch, TS-1187A and other footprints come from the KiCad standard library | Check the JLC 3D preview / DFM before assembly |
| 5 | MGM210P has low LCSC stock and ships blank | Consign it from DigiKey; program the bootloader and firmware over SWD at the factory |
| 6 | Generic USB-C supplies give 5 V / 3 A, which limits USB port current | Use the Raspberry Pi 27 W USB-C supply (5 V / 5 A). `usb_max_current_enable=1` is set |
| 7 | Speaker and mic are in the same lid, so echo can cause false wake-ups | Gasket the mic tube; tune mic gain and noise suppression in the Assist Satellite options |
| 8 | Enclosure fit tolerances depend on the printer | Print the lid first and check the connector openings against the assembled board |
| 9 | `hvh_provision.py` uses Home Assistant APIs that change between releases; it has not been run against a live system | Every step can be skipped; the README steps can be done by hand in the UI |
| 10 | The CONFIG/network keyfile replaces all network connections at every boot |
| 11 | ESD channel choices: on U5 (USB3 ESD) the unused flow-through pads 7/9 are tied to GND. On U14 (Ethernet ESD), ETH2 uses pads 9/10. The TPD4EUSB30 pads 6/7/9/10 have no internal connection | Confirm against the TI datasheet during the EE review |
| 12 | 34 reference labels are hidden on the top silkscreen to avoid overlaps | Use the assembly PDFs, which show every reference, for bring-up and rework | Delete `CONFIG/network` from the boot partition after the first boot if you manage Wi-Fi in the UI |

## Rebuilding from source

All generators are in `gen/`. KiCad 7 Python (`pcbnew`), numba, shapely and CadQuery are needed.

```
python3 footprints.py && python3 schematic.py && python3 verify_sch.py   # library, schematic, netlist check
python3 pcb_place.py                                                      # board, placement, rules, planes
python3 router.py ../kicad/hvh.kicad_pcb routed.kicad_pcb                # grid router, 3 signal layers (about 1 h)
python3 repair.py routed.kicad_pcb repaired.kicad_pcb 25                  # rip-up/re-route hill climb on what is left
python3 postfix.py repaired.kicad_pcb fixed.kicad_pcb fix                 # GND via-in-pad, +5V stitching
python3 pcb_finish.py fixed.kicad_pcb ../kicad/hvh.kicad_pcb              # planes/pours, silkscreen, zone fill
python3 drc.py ../kicad/hvh.kicad_pcb drc.txt && python3 silkfix.py ../kicad/hvh.kicad_pcb drc.txt
python3 fab.py <pcb> ../kicad/hvh.kicad_sch ../fab                        # manufacturing outputs
python3 enclosure.py ../enclosure                                         # STL / 3MF / STEP
```
