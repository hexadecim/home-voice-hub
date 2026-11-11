"""
HVH-1 Home Voice Hub - single source of truth for the electrical design.

Everything downstream (symbols, schematic, netlist, PCB, BOM, CPL) is generated
from the PARTS catalogue and the COMPONENTS list in this file.

Conventions
  * Net names are global. "NC" means the pin is intentionally unconnected.
  * Custom ICs/connectors get generated symbols whose pin numbers are copied
    from the footprint, so schematic pin == footprint pad by construction.
"""

# --------------------------------------------------------------------------
# Part catalogue: key -> sourcing + footprint
# lcsc: JLCPCB/LCSC part number (assembly), dist: other distributor info
# --------------------------------------------------------------------------
P = {}
def part(key, value, fp, lcsc, mpn, mfr, desc, bom=True, dist="", note=""):
    P[key] = dict(value=value, fp=fp, lcsc=lcsc, mpn=mpn, mfr=mfr, desc=desc,
                  bom=bom, dist=dist, note=note)

# ---- passives (JLC basic / preferred where possible) ----
part("R0_0402",    "0R",    "Resistor_SMD:R_0402_1005Metric", "C17168", "0402WGF0000TCE", "UNI-ROYAL", "Resistor 0R 0402")
part("R22_0402",   "22R",   "Resistor_SMD:R_0402_1005Metric", "C25092", "0402WGF220JTCE", "UNI-ROYAL", "Resistor 22R 1% 0402")
part("R100_0402",  "100R",  "Resistor_SMD:R_0402_1005Metric", "C25076", "0402WGF1000TCE", "UNI-ROYAL", "Resistor 100R 1% 0402")
part("R470_0402",  "470R",  "Resistor_SMD:R_0402_1005Metric", "C25117", "0402WGF4700TCE", "UNI-ROYAL", "Resistor 470R 1% 0402")
part("R1k_0402",   "1k",    "Resistor_SMD:R_0402_1005Metric", "C11702", "0402WGF1001TCE", "UNI-ROYAL", "Resistor 1k 1% 0402")
part("R1k5_0402",  "1k5",   "Resistor_SMD:R_0402_1005Metric", "C25867", "0402WGF1501TCE", "UNI-ROYAL", "Resistor 1.5k 1% 0402")
part("R2k7_0402",  "2k7 1%","Resistor_SMD:R_0402_1005Metric", "C25885", "0402WGF2701TCE", "UNI-ROYAL", "Resistor 2.7k 1% 0402")
part("R10k_0402",  "10k",   "Resistor_SMD:R_0402_1005Metric", "C25744", "0402WGF1002TCE", "UNI-ROYAL", "Resistor 10k 1% 0402")
part("R26k1_0402", "26k1 1%","Resistor_SMD:R_0402_1005Metric","C155697","RC0402FR-0726K1L","YAGEO", "Resistor 26.1k 1% 0402 (TPS2553 ILIM ~1.0A)")
part("R47k_0402",  "47k",   "Resistor_SMD:R_0402_1005Metric", "C25792", "0402WGF4702TCE", "UNI-ROYAL", "Resistor 47k 1% 0402")
part("R68k_0402",  "68k",   "Resistor_SMD:R_0402_1005Metric", "C36871", "0402WGF6802TCE", "UNI-ROYAL", "Resistor 68k 1% 0402")
part("R100k_0402", "100k",  "Resistor_SMD:R_0402_1005Metric", "C25741", "0402WGF1003TCE", "UNI-ROYAL", "Resistor 100k 1% 0402")
part("R1M_0402",   "1M",    "Resistor_SMD:R_0402_1005Metric", "C26083", "0402WGF1004TCE", "UNI-ROYAL", "Resistor 1M 1% 0402")

part("C27p_0402",  "27pF",  "Capacitor_SMD:C_0402_1005Metric", "C1557",  "0402CG270J500NT", "FH", "Cap 27pF 50V C0G 0402")
part("C10n_0402",  "10nF",  "Capacitor_SMD:C_0402_1005Metric", "C15195", "CL05B103KB5NNNC", "Samsung", "Cap 10nF 50V X7R 0402")
part("C100n_0402", "100nF", "Capacitor_SMD:C_0402_1005Metric", "C1525",  "CL05B104KO5NNNC", "Samsung", "Cap 100nF 16V X7R 0402")
part("C1u_0402",   "1uF",   "Capacitor_SMD:C_0402_1005Metric", "C52923", "CL05A105KA5NQNC", "Samsung", "Cap 1uF 25V X5R 0402")
part("C4u7_0603",  "4.7uF", "Capacitor_SMD:C_0603_1608Metric", "C19666", "CL10A475KO8NNNC", "Samsung", "Cap 4.7uF 16V X5R 0603")
part("C10u_0603",  "10uF",  "Capacitor_SMD:C_0603_1608Metric", "C19702", "CL10A106KP8NNNC", "Samsung", "Cap 10uF 10V X5R 0603")
part("C10u_0805",  "10uF",  "Capacitor_SMD:C_0805_2012Metric", "C15850", "CL21A106KAYNNNE", "Samsung", "Cap 10uF 25V X5R 0805")
part("C22u_0805",  "22uF",  "Capacitor_SMD:C_0805_2012Metric", "C45783", "CL21A226MAQNNNE", "Samsung", "Cap 22uF 25V X5R 0805")
part("C47u_1206",  "47uF",  "Capacitor_SMD:C_1206_3216Metric", "C68361", "CL31A476MQHNNNE", "Samsung", "Cap 47uF 6.3V X5R 1206")

part("FB600_0603", "600R@100MHz", "Inductor_SMD:L_0603_1608Metric", "C1002", "GZ1608D601TF", "Sunlord", "Ferrite bead 600R 200mA 0603")
part("LED_R",  "Red",   "LED_SMD:LED_0603_1608Metric", "C2286",   "KT-0603R",      "KENTO",     "LED red 0603")
part("LED_G",  "Green", "LED_SMD:LED_0603_1608Metric", "C965804", "XL-1608UGC-04", "XINGLIGHT", "LED green 0603")
part("LED_B",  "Blue",  "LED_SMD:LED_0603_1608Metric", "C965807", "XL-1608UBC-04", "XINGLIGHT", "LED blue 0603")
part("TVS5V",  "SMF5.0A", "Diode_SMD:D_SMF", "C193402", "SMF5.0A", "LGE/various", "TVS 5V unidirectional 200W SOD-123FL")
part("XTAL12M","12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C9002", "X322512MSB4SI", "Yangxing", "Crystal 12MHz 20pF 3225")

# ---- ICs ----
part("TPD4EUSB30", "TPD4EUSB30", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", "C90627", "TPD4EUSB30DQAR", "Texas Instruments", "4-ch low-cap ESD (USB3/Ethernet)")
part("TLV75533",  "TLV75533P", "Package_TO_SOT_SMD:SOT-23-5", "C404027", "TLV75533PDBVR", "Texas Instruments", "LDO 3.3V 500mA")
part("TPS2553",   "TPS2553",   "Package_TO_SOT_SMD:SOT-23-6", "C55266",  "TPS2553DBVR",  "Texas Instruments", "USB power switch, adj. ILIM")
part("RT9742",    "RT9742GGJ5","Package_TO_SOT_SMD:SOT-23-5", "C250547", "RT9742GGJ5",   "Richtek", "SD card power switch")
part("FE11S",     "FE1.1s",    "Package_SO:SSOP-28_3.9x9.9mm_P0.635mm", "C9359", "FE1.1S-BSOP28BCN", "Terminus", "USB2.0 4-port MTT hub")
part("CM108B",    "CM108B",    "Package_QFP:LQFP-48_7x7mm_P0.5mm", "C371347", "CM108B", "C-Media", "USB audio codec (mic in / line out)")
part("PAM8302",   "PAM8302A",  "Package_SO:MSOP-8_3x3mm_P0.65mm", "C113367", "PAM8302AASCR", "Diodes Inc", "2.5W mono class-D amplifier")
part("CP2102N",   "CP2102N",   "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm", "C969151", "CP2102N-A02-GQFN24R", "Silicon Labs", "USB-UART bridge")
part("MGM210P",   "MGM210PA32JIA2", "hvh:SiliconLabs_MGM210P", "C1864147", "MGM210PA32JIA2", "Silicon Labs",
     "Zigbee/Thread module EFR32MG21 +20dBm, chip antenna (same module as HA Yellow)",
     dist="DigiKey 336-MGM210PA32JIA2-ND / Farnell 3463094 (R variant)", note="Low LCSC stock: order via JLC Global Sourcing or consign from DigiKey")
part("ZTS6216",   "ZTS6216",   "hvh:MIC_ZTS6216", "C481302", "ZTS6216", "ZILLTEK", "Analog MEMS microphone, top port, -38dBV, 65dB SNR")

# ---- connectors / electromech ----
part("USBC",   "USB-C PWR", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948", "TYPE-C-31-M-12", "Korean Hroparts", "USB-C receptacle 16P")
part("USBA",   "USB-A",     "hvh:USB3_A_Amphenol_GSB311131HR", "C473057", "GSB311131HR", "Amphenol", "USB 3.0 Type-A receptacle, R/A THT")
part("RJ45",   "RJ45 1G",   "hvh:RJ45_HanRun_HR911130A", "C54408", "HR911130A", "HanRun", "RJ45 gigabit MagJack with LEDs")
part("USDSOCK","microSD",   "Connector_Card:microSD_HC_Molex_104031-0811", "C585350", "1040310811", "Molex", "microSD push-pull socket")
part("DF40",   "DF40C-100DS","hvh:CM5_DF40C-100DS-0.4V", "C597931", "DF40C-100DS-0.4V(51)", "Hirose", "CM5 board-to-board receptacle 100P 0.4mm 1.5mm stack")
part("CM5MECH","CM5 module", "hvh:CM5_Module_Mechanical", "", "CM5104000 (CM5 Lite, Wireless, 4GB)", "Raspberry Pi",
     "Compute Module 5 - plugs into J10/J11 (not soldered)", bom=False,
     dist="Raspberry Pi approved resellers (CM5104000 / CM5102000 / CM5108000)")
part("JST_PH2","SPEAKER",   "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal", "C173752", "S2B-PH-K-S(LF)(SN)", "JST", "JST PH 2P R/A (speaker 4-8 ohm, 2W)")
part("JST_SH4","FAN",       "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "C160404", "SM04B-SRSS-TB(LF)(SN)", "JST", "JST SH 4P R/A (Pi fan)")
part("JST_SH2","RTC BAT",   "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal", "C160402", "SM02B-SRSS-TB(LF)(SN)", "JST", "JST SH 2P R/A (Pi RTC battery)")
part("TACT",   "TS-1187A",  "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "C318884", "TS-1187A-B-A-B", "XKB", "Tactile switch 5.1x5.1mm SMD")
part("SLIDE",  "PCM12SMTR", "Button_Switch_SMD:SW_SPDT_PCM12", "C221841", "PCM12SMTR", "C&K", "SPDT slide switch R/A (mic privacy)")
part("TP",     "TP",        "TestPoint:TestPoint_Pad_D1.0mm", "", "", "", "Test pad", bom=False)
part("MH_M3",  "M3",        "MountingHole:MountingHole_3.2mm_M3_Pad_Via", "", "", "", "Mounting hole M3, GND", bom=False)
part("FID",    "FID",       "Fiducial:Fiducial_1mm_Mask2mm", "", "", "", "Fiducial", bom=False)

# --------------------------------------------------------------------------
# Custom symbol pin definitions  (pin number, name, electrical type, side)
# side: L/R/T/B on the generated rectangle
# --------------------------------------------------------------------------
SYM = {}

def cm5_half(lo):
    """CM5 pins lo..lo+99, named from the CM5 datasheet pinout."""
    return [(str(n - lo + 1), CM5_PIN_NAMES[n]) for n in range(lo, lo + 100)]

CM5_PIN_NAMES = {}
_cm5 = """1 GND|2 GND|3 Ethernet_Pair3_P|4 Ethernet_Pair1_P|5 Ethernet_Pair3_N|6 Ethernet_Pair1_N|7 GND|8 GND|9 Ethernet_Pair2_N|10 Ethernet_Pair0_N|11 Ethernet_Pair2_P|12 Ethernet_Pair0_P|13 GND|14 GND|15 Ethernet_nLED3|16 FAN_TACHO|17 Ethernet_nLED2|18 Ethernet_SYNC_OUT|19 FAN_PWM|20 EEPROM_nWP|21 LED_nACT|22 GND|23 GND|24 GPIO26|25 GPIO21|26 GPIO19|27 GPIO20|28 GPIO13|29 GPIO16|30 GPIO6|31 GPIO12|32 GND|33 GND|34 GPIO5|35 ID_SC|36 ID_SD|37 GPIO7|38 GPIO11|39 GPIO8|40 GPIO9|41 GPIO25|42 GND|43 GND|44 GPIO10|45 GPIO24|46 GPIO22|47 GPIO23|48 GPIO27|49 GPIO18|50 GPIO17|51 GPIO15|52 GND|53 GND|54 GPIO4|55 GPIO14|56 GPIO3|57 SD_CLK|58 GPIO2|59 GND|60 GND|61 SD_DAT3|62 SD_CMD|63 SD_DAT0|64 SD_DAT5|65 GND|66 GND|67 SD_DAT1|68 SD_DAT4|69 SD_DAT2|70 SD_DAT7|71 GND|72 SD_DAT6|73 SD_VDD_OVERRIDE|74 GND|75 SD_PWR_ON|76 VBAT|77 +5V_IN|78 GPIO_VREF|79 +5V_IN|80 SCL0|81 +5V_IN|82 SDA0|83 +5V_IN|84 CM5_3V3_OUT|85 +5V_IN|86 CM5_3V3_OUT|87 +5V_IN|88 CM5_1V8_OUT|89 WiFi_nDisable|90 CM5_1V8_OUT|91 BT_nDisable|92 PWR_BUT|93 nRPIBOOT|94 CC1|95 LED_nPWR|96 CC2|97 CAM_GPIO0|98 GND|99 PMIC_ENABLE|100 CAM_GPIO1|101 USB_OTG_ID|102 PCIe_nCLKREQ|103 USB2_N|104 PCIE_nWAKE|105 USB2_P|106 PCIE_PWR_EN|107 GND|108 GND|109 PCIe_nRST|110 PCIe_CLK_P|111 VBUS_EN|112 PCIe_CLK_N|113 GND|114 GND|115 MIPI0_D0_N|116 PCIe_RX_P|117 MIPI0_D0_P|118 PCIe_RX_N|119 GND|120 GND|121 MIPI0_D1_N|122 PCIe_TX_P|123 MIPI0_D1_P|124 PCIe_TX_N|125 GND|126 GND|127 MIPI0_C_N|128 USB3-0-RX_N|129 MIPI0_C_P|130 USB3-0-RX_P|131 GND|132 GND|133 MIPI0_D2_N|134 USB3-0-D_P|135 MIPI0_D2_P|136 USB3-0-D_N|137 GND|138 GND|139 MIPI0_D3_N|140 USB3-0-TX_N|141 MIPI0_D3_P|142 USB3-0-TX_P|143 HDMI1_HOTPLUG|144 GND|145 HDMI1_SDA|146 HDMI1_TX2_P|147 HDMI1_SCL|148 HDMI1_TX2_N|149 HDMI1_CEC|150 GND|151 HDMI0_CEC|152 HDMI1_TX1_P|153 HDMI0_HOTPLUG|154 HDMI1_TX1_N|155 GND|156 GND|157 USB3-1-RX_N|158 HDMI1_TX0_P|159 USB3-1-RX_P|160 HDMI1_TX0_N|161 GND|162 GND|163 USB3-1-D_P|164 HDMI1_CLK_P|165 USB3-1-D_N|166 HDMI1_CLK_N|167 GND|168 GND|169 USB3-1-TX_N|170 HDMI0_TX2_P|171 USB3-1-TX_P|172 HDMI0_TX2_N|173 GND|174 GND|175 MIPI1_D0_N|176 HDMI0_TX1_P|177 MIPI1_D0_P|178 HDMI0_TX1_N|179 GND|180 GND|181 MIPI1_D1_N|182 HDMI0_TX0_P|183 MIPI1_D1_P|184 HDMI0_TX0_N|185 GND|186 GND|187 MIPI1_C_N|188 HDMI0_CLK_P|189 MIPI1_C_P|190 HDMI0_CLK_N|191 GND|192 GND|193 MIPI1_D2_N|194 MIPI1_D3_N|195 MIPI1_D2_P|196 MIPI1_D3_P|197 GND|198 GND|199 HDMI0_SDA|200 HDMI0_SCL"""
for tok in _cm5.split("|"):
    n, name = tok.split(" ", 1)
    CM5_PIN_NAMES[int(n)] = name

def _cm5_sym(lo):
    pins = []
    for n in range(lo, lo + 100):
        name = CM5_PIN_NAMES[n]
        num = str(n - lo + 1)
        if name == "GND":
            t = "power_in"
        elif name == "+5V_IN":
            t = "power_in"
        elif name in ("CM5_3V3_OUT", "CM5_1V8_OUT"):
            t = "power_out"
        else:
            t = "bidirectional"
        side = "L" if (n - lo) % 2 == 0 else "R"   # odd CM5 pins left, even right
        pins.append((num, f"{name}", t, side))
    return pins

SYM["CM5_A"] = dict(ref="J", pins=_cm5_sym(1), title="CM5 connector A (pins 1-100)")
SYM["CM5_B"] = dict(ref="J", pins=_cm5_sym(101), title="CM5 connector B (pins 101-200)")

SYM["TPD4EUSB30"] = dict(ref="U", pins=[
    ("1","D1+","passive","L"),("10","D1+_THRU","passive","R"),
    ("2","D1-","passive","L"),("9","D1-_THRU","passive","R"),
    ("4","D2+","passive","L"),("7","D2+_THRU","passive","R"),
    ("5","D2-","passive","L"),("6","D2-_THRU","passive","R"),
    ("3","GND","power_in","B"),("8","GND","passive","B")])

SYM["TLV75533"] = dict(ref="U", pins=[("1","IN","power_in","L"),("3","EN","input","L"),("2","GND","power_in","B"),("4","NC","no_connect","R"),("5","OUT","power_out","R")])
SYM["TPS2553"]  = dict(ref="U", pins=[("1","IN","power_in","L"),("3","EN","input","L"),("5","ILIM","passive","L"),("2","GND","power_in","B"),("6","OUT","power_out","R"),("4","~{FAULT}","open_collector","R")])
SYM["RT9742"]   = dict(ref="U", pins=[("5","IN","power_in","L"),("4","EN","input","L"),("2","GND","power_in","B"),("1","OUT","power_out","R"),("3","~{FLG}","open_collector","R")])

SYM["FE11S"] = dict(ref="U", pins=[
    ("20","VDD5","power_in","L"),("21","VD33F","power_out","L"),("16","DPU","bidirectional","L"),("15","DMU","bidirectional","L"),
    ("17","~{XRSTJ}","input","L"),("18","VBUSM","input","L"),("19","BUSJ","input","L"),("26","~{OVCJ}","input","L"),
    ("3","XIN","input","L"),("2","XOUT","output","L"),("14","REXT","passive","L"),
    ("11","DP1","bidirectional","R"),("10","DM1","bidirectional","R"),("9","DP2","bidirectional","R"),("8","DM2","bidirectional","R"),
    ("7","DP3","bidirectional","R"),("6","DM3","bidirectional","R"),("5","DP4","bidirectional","R"),("4","DM4","bidirectional","R"),
    ("22","DRV/CHRGEN","bidirectional","R"),("23","LED1","bidirectional","R"),("24","LED2","bidirectional","R"),
    ("25","~{PWRJ}","open_collector","R"),("27","~{TESTJ}","bidirectional","R"),
    ("12","NC","no_connect","R"),("13","NC","no_connect","R"),("28","NC","no_connect","R"),
    ("1","VSS","power_in","B")])

_cm108 = [("29","AVDD","power_in","L"),("34","AVDD","power_in","L"),("35","DVDD","power_in","L"),("37","REGV","power_out","L"),
          ("7","PWRSEL","input","L"),("38","MSEL","input","L"),("41","USBDP","bidirectional","L"),("42","USBDM","bidirectional","L"),
          ("8","XI","input","L"),("9","XO","output","L"),("10","MODE","input","L"),("16","SDIN","input","L"),("22","ADSEL","input","L"),
          ("23","TEST","input","L"),("28","VSEL","input","L"),
          ("27","MICIN","input","R"),("25","VBIAS","output","R"),("26","VREF","passive","R"),("30","LOL","output","R"),("32","LOR","output","R"),
          ("31","LOBS","passive","R"),("6","MUTER","input","R"),("18","MUTEP","input","R"),("39","VOLUP","input","R"),("48","VOLDN","input","R"),
          ("40","PDSW","input","R"),("12","LEDO","output","R"),("21","LEDR","output","R"),("43","GPIO1","bidirectional","R"),("11","GPIO2","bidirectional","R"),
          ("13","GPIO3","bidirectional","R"),("15","GPIO4","bidirectional","R"),("1","SPDIFO","output","R"),("2","DR","input","R"),("3","DW","output","R"),
          ("4","SK","output","R"),("5","CS","output","R"),("17","ADSCLS","output","R"),("19","ADLRCK","output","R"),("20","ADMCLK","output","R"),
          ("44","SDOUT","output","R"),("45","DAMCLK","output","R"),("46","DALRCK","output","R"),("47","DASCLK","output","R"),
          ("14","DVSS","power_in","B"),("24","AVSS","power_in","B"),("33","AVSS","power_in","B"),("36","DVSS","power_in","B")]
SYM["CM108B"] = dict(ref="U", pins=_cm108)

SYM["PAM8302"] = dict(ref="U", pins=[("6","VDD","power_in","L"),("1","~{SD}","input","L"),("3","IN+","input","L"),("4","IN-","input","L"),
                                      ("2","NC","no_connect","R"),("5","VO+","output","R"),("8","VO-","output","R"),("7","GND","power_in","B")])

SYM["CP2102N"] = dict(ref="U", pins=[("6","VDD","power_in","L"),("7","VREGIN","power_in","L"),("5","VIO","power_in","L"),("8","VBUS","input","L"),
                                      ("3","D+","bidirectional","L"),("4","D-","bidirectional","L"),("9","~{RST}","input","L"),
                                      ("21","TXD","output","R"),("20","RXD","input","R"),("19","~{RTS}","output","R"),("18","~{CTS}","input","R"),
                                      ("23","~{DTR}","output","R"),("22","~{DSR}","input","R"),("24","~{DCD}","input","R"),("1","~{RI}/CLK","input","R"),
                                      ("14","GPIO.0/TXT","bidirectional","R"),("13","GPIO.1/RXT","bidirectional","R"),("12","GPIO.2/RS485","bidirectional","R"),
                                      ("11","GPIO.3/~{WAKEUP}","bidirectional","R"),("15","~{SUSPEND}","output","R"),("17","SUSPEND","output","R"),
                                      ("10","NC","no_connect","R"),("16","NC","no_connect","R"),
                                      ("2","GND","power_in","B"),("25","EP","passive","B")])

_mgm = [("13","VDD","power_in","L"),("14","IOVDD","power_in","L"),("27","RESETn","input","L"),("11","DECOUPLE","passive","L"),
        ("9","PA05/TX","bidirectional","L"),("10","PA06/RX","bidirectional","L"),("17","PD02/CTS","bidirectional","L"),("22","PC01/RTS","bidirectional","L"),
        ("3","PB00/BTL","bidirectional","L"),("2","PB01/LED","bidirectional","L"),
        ("5","PA01/SWCLK","bidirectional","R"),("6","PA02/SWDIO","bidirectional","R"),("7","PA03/SWO","bidirectional","R"),
        ("4","PA00","bidirectional","R"),("8","PA04","bidirectional","R"),("15","PD04","bidirectional","R"),("16","PD03","bidirectional","R"),
        ("18","PD01","bidirectional","R"),("19","PD00","bidirectional","R"),("21","PC00","bidirectional","R"),("23","PC02","bidirectional","R"),
        ("24","PC03","bidirectional","R"),("25","PC04","bidirectional","R"),("26","PC05","bidirectional","R"),("29","RF2G4_IO2","passive","R"),
        ("1","GND","power_in","B"),("12","GND","passive","B"),("20","GND","passive","B"),("28","GND","passive","B"),("30","GND","passive","B"),("31","GND","passive","B")]
SYM["MGM210P"] = dict(ref="U", pins=_mgm)

SYM["ZTS6216"] = dict(ref="MK", pins=[("4","VDD","power_in","L"),("1","OUT","output","R"),("2","GND","power_in","B"),("3","GND","passive","B")])

SYM["USBC"] = dict(ref="J", pins=[("A4","VBUS","passive","L"),("A9","VBUS","passive","L"),("B4","VBUS","passive","L"),("B9","VBUS","passive","L"),
                                   ("A5","CC1","bidirectional","L"),("B5","CC2","bidirectional","L"),
                                   ("A6","D+","bidirectional","R"),("B6","D+","bidirectional","R"),("A7","D-","bidirectional","R"),("B7","D-","bidirectional","R"),
                                   ("A8","SBU1","bidirectional","R"),("B8","SBU2","bidirectional","R"),
                                   ("A1","GND","passive","B"),("A12","GND","passive","B"),("B1","GND","passive","B"),("B12","GND","passive","B"),("S1","SHIELD","passive","B")])
SYM["USBA"] = dict(ref="J", pins=[("1","VBUS","passive","L"),("2","D-","bidirectional","L"),("3","D+","bidirectional","L"),("4","GND","passive","L"),
                                   ("5","SSRX-","bidirectional","R"),("6","SSRX+","bidirectional","R"),("7","GND_DRAIN","passive","R"),
                                   ("8","SSTX-","bidirectional","R"),("9","SSTX+","bidirectional","R"),("10","SHIELD","passive","B")])
SYM["RJ45"] = dict(ref="J", pins=[("P2","MDI0+","passive","L"),("P3","MDI0-","passive","L"),("P4","MDI1+","passive","L"),("P7","MDI1-","passive","L"),
                                   ("P5","MDI2+","passive","L"),("P6","MDI2-","passive","L"),("P8","MDI3+","passive","L"),("P9","MDI3-","passive","L"),
                                   ("P1","CT_A","passive","R"),("P10","CT_B","passive","R"),
                                   ("11","LED1_A","passive","R"),("12","LED1_K","passive","R"),("14","LED2_A","passive","R"),("13","LED2_K","passive","R"),
                                   ("SHIELD0","SHIELD","passive","B"),("SHIELD1","SHIELD","passive","B")])
SYM["USDSOCK"] = dict(ref="J", pins=[("4","VDD","power_in","L"),("5","CLK","input","L"),("3","CMD","bidirectional","L"),("7","DAT0","bidirectional","L"),
                                      ("8","DAT1","bidirectional","L"),("1","DAT2","bidirectional","L"),("2","DAT3/CD","bidirectional","L"),
                                      ("9","DET_B","passive","R"),("10","DET_A","passive","R"),("6","VSS","power_in","B"),("11","SHIELD","passive","B")])
SYM["DF40_MECH"] = dict(ref="M", pins=[])

# ---- generic 2/3/4-pin connector & switch symbols ----
SYM["CONN2"] = dict(ref="J", pins=[("1","1","passive","L"),("2","2","passive","L")])
SYM["CONN2MP"] = dict(ref="J", pins=[("1","1","passive","L"),("2","2","passive","L"),("MP","MP","passive","B")])
SYM["CONN4MP"] = dict(ref="J", pins=[("1","1","passive","L"),("2","2","passive","L"),("3","3","passive","L"),("4","4","passive","L"),("MP","MP","passive","B")])
SYM["TACT"] = dict(ref="SW", pins=[("1","1","passive","L"),("2","2","passive","R")])
SYM["SPDT"] = dict(ref="SW", pins=[("2","COM","passive","L"),("1","A","passive","R"),("3","B","passive","R")])
SYM["TP"] = dict(ref="TP", pins=[("1","1","passive","L")])
SYM["MH"] = dict(ref="H", pins=[("1","1","passive","B")])
SYM["FID"] = dict(ref="FID", pins=[])
SYM["XTAL4"] = dict(ref="Y", pins=[("1","X1","passive","L"),("3","X2","passive","R"),("2","GND","passive","B"),("4","GND","passive","B")])

# KiCad stock symbols used for 2-terminal passives
STOCK = {"R": "Device:R", "C": "Device:C", "LED": "Device:LED", "FB": "Device:FerriteBead_Small", "TVS": "Device:D_TVS"}

# --------------------------------------------------------------------------
# Components: (ref, part key, symbol key, {pin: net}, sheet)
# --------------------------------------------------------------------------
COMPONENTS = []
SHEETS = ["power", "cm5", "usb", "audio", "zigbee", "eth_sd", "ui"]
SHEET_TITLES = {"power": "Power input / USB-C / 3.3V",
                "cm5": "Raspberry Pi CM5 connectors",
                "usb": "USB-A ports and USB 2.0 hub",
                "audio": "USB audio: microphone and speaker",
                "zigbee": "Zigbee / Thread radio",
                "eth_sd": "Gigabit Ethernet and microSD",
                "ui": "Buttons, LEDs, fan, RTC, test points, mechanics"}

def comp(ref, pkey, skey, pins, sheet):
    COMPONENTS.append(dict(ref=ref, part=pkey, sym=skey, pins=pins, sheet=sheet))

def R(ref, pkey, a, b, sheet):   comp(ref, pkey, "R", {"1": a, "2": b}, sheet)
def C(ref, pkey, a, b, sheet):   comp(ref, pkey, "C", {"1": a, "2": b}, sheet)
def LED(ref, pkey, anode, cathode, sheet): comp(ref, pkey, "LED", {"1": cathode, "2": anode}, sheet)  # KiCad LED fp: 1=K 2=A
def TP(ref, net, sheet): comp(ref, "TP", "TP", {"1": net}, sheet)

# ===================== POWER =====================
comp("J1", "USBC", "USBC", {"A4": "+5V", "A9": "+5V", "B4": "+5V", "B9": "+5V",
                             "A5": "CC1", "B5": "CC2", "A6": "USBC_DP", "B6": "USBC_DP",
                             "A7": "USBC_DN", "B7": "USBC_DN", "A8": "NC", "B8": "NC",
                             "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND"}, "power")
comp("D1", "TVS5V", "TVS", {"1": "+5V", "2": "GND"}, "power")   # 1 = cathode
C("C1", "C47u_1206", "+5V", "GND", "power")
C("C2", "C22u_0805", "+5V", "GND", "power")
C("C3", "C100n_0402", "+5V", "GND", "power")
comp("U1", "TPD4EUSB30", "TPD4EUSB30", {"1": "USBC_DP", "10": "NC", "2": "USBC_DN", "9": "NC",
                                         "4": "CC1", "7": "NC", "5": "CC2", "6": "NC", "3": "GND", "8": "GND"}, "power")
comp("U2", "TLV75533", "TLV75533", {"1": "+5V", "3": "+5V", "2": "GND", "4": "NC", "5": "+3V3A"}, "power")
C("C4", "C1u_0402", "+5V", "GND", "power")
C("C5", "C4u7_0603", "+3V3A", "GND", "power")
C("C6", "C100n_0402", "+3V3A", "GND", "power")

# ===================== CM5 =====================
cmA = {}
cmB = {}
def cm(pin, net):
    if pin <= 100: cmA[str(pin)] = net
    else: cmB[str(pin - 100)] = net
for n, name in CM5_PIN_NAMES.items():
    cm(n, "GND" if name == "GND" else "NC")
for n in (77, 79, 81, 83, 85, 87): cm(n, "+5V")
for n in (84, 86): cm(n, "+3V3")
cm(88, "NC"); cm(90, "NC")
cm(3, "ETH3_P"); cm(5, "ETH3_N"); cm(4, "ETH1_P"); cm(6, "ETH1_N")
cm(11, "ETH2_P"); cm(9, "ETH2_N"); cm(12, "ETH0_P"); cm(10, "ETH0_N")
cm(15, "ETH_LED3_N"); cm(17, "ETH_LED2_N")
cm(16, "FAN_TACH"); cm(19, "FAN_PWM"); cm(21, "LED_ACT_N")
cm(55, "DBG_TX"); cm(51, "DBG_RX")
cm(57, "SD_CLK"); cm(61, "SD_D3"); cm(62, "SD_CMD"); cm(63, "SD_D0"); cm(67, "SD_D1"); cm(69, "SD_D2")
cm(75, "SD_PWR_ON"); cm(76, "VBAT"); cm(78, "GPIO_VREF")
cm(92, "PWR_BUT"); cm(93, "nRPIBOOT"); cm(94, "CC1"); cm(95, "LED_PWR_N"); cm(96, "CC2")
cm(103, "USBC_DN"); cm(105, "USBC_DP"); cm(111, "VBUS_EN")
cm(128, "USB3A_RX_N"); cm(130, "USB3A_RX_P"); cm(134, "USB3A_DP"); cm(136, "USB3A_DN")
cm(140, "USB3A_TX_N"); cm(142, "USB3A_TX_P")
cm(163, "HUB_UP_P"); cm(165, "HUB_UP_N")
comp("J10", "DF40", "CM5_A", cmA, "cm5")
comp("J11", "DF40", "CM5_B", cmB, "cm5")
comp("M1", "CM5MECH", "DF40_MECH", {}, "cm5")
R("R1", "R0_0402", "+3V3", "GPIO_VREF", "cm5")
C("C7", "C47u_1206", "+5V", "GND", "cm5")
C("C8", "C10u_0805", "+5V", "GND", "cm5")
C("C10", "C4u7_0603", "+3V3", "GND", "cm5")
C("C11", "C100n_0402", "+3V3", "GND", "cm5")

# ===================== USB =====================
comp("J3", "USBA", "USBA", {"1": "USB1_VBUS", "2": "USB3A_DN", "3": "USB3A_DP", "4": "GND",
                             "5": "USB3A_RX_N", "6": "USB3A_RX_P", "7": "GND", "8": "USB3A_TX_N", "9": "USB3A_TX_P", "10": "GND"}, "usb")
comp("J4", "USBA", "USBA", {"1": "USB2_VBUS", "2": "USB2A_DN", "3": "USB2A_DP", "4": "GND",
                             "5": "NC", "6": "NC", "7": "GND", "8": "NC", "9": "NC", "10": "GND"}, "usb")
comp("U3", "TPS2553", "TPS2553", {"1": "+5V", "3": "VBUS_EN", "5": "ILIM1", "2": "GND", "6": "USB1_VBUS", "4": "NC"}, "usb")
comp("U4", "TPS2553", "TPS2553", {"1": "+5V", "3": "VBUS_EN", "5": "ILIM2", "2": "GND", "6": "USB2_VBUS", "4": "NC"}, "usb")
R("R2", "R26k1_0402", "ILIM1", "GND", "usb")
R("R3", "R26k1_0402", "ILIM2", "GND", "usb")
C("C12", "C1u_0402", "+5V", "GND", "usb")
C("C13", "C47u_1206", "USB1_VBUS", "GND", "usb")
C("C14", "C100n_0402", "USB1_VBUS", "GND", "usb")
C("C15", "C47u_1206", "USB2_VBUS", "GND", "usb")
C("C16", "C100n_0402", "USB2_VBUS", "GND", "usb")
comp("U5", "TPD4EUSB30", "TPD4EUSB30", {"1": "USB3A_TX_P", "10": "NC", "2": "USB3A_TX_N", "9": "GND",
                                         "4": "USB3A_RX_P", "7": "GND", "5": "USB3A_RX_N", "6": "NC", "3": "GND", "8": "GND"}, "usb")
comp("U6", "TPD4EUSB30", "TPD4EUSB30", {"1": "USB3A_DP", "10": "NC", "2": "USB3A_DN", "9": "NC",
                                         "4": "NC", "7": "NC", "5": "NC", "6": "NC", "3": "GND", "8": "GND"}, "usb")
comp("U15", "TPD4EUSB30", "TPD4EUSB30", {"1": "USB2A_DP", "10": "NC", "2": "USB2A_DN", "9": "NC",
                                          "4": "NC", "7": "NC", "5": "NC", "6": "NC", "3": "GND", "8": "GND"}, "usb")
comp("U7", "FE11S", "FE11S", {"20": "+5V", "21": "HUB_3V3", "16": "HUB_UP_P", "15": "HUB_UP_N",
                               "17": "HUB_RST_N", "18": "HUB_VBUSM", "19": "HUB_BUSJ", "26": "HUB_OVC_N",
                               "3": "HUB_XIN", "2": "HUB_XOUT", "14": "HUB_REXT",
                               "11": "USB2A_DP", "10": "USB2A_DN", "9": "AUD_USB_P", "8": "AUD_USB_N",
                               "7": "ZB_USB_P", "6": "ZB_USB_N", "5": "HUB_D4_P", "4": "HUB_D4_N",
                               "22": "NC", "23": "NC", "24": "NC", "25": "NC", "27": "NC", "12": "NC", "13": "NC", "28": "NC",
                               "1": "GND"}, "usb")
comp("Y1", "XTAL12M", "XTAL4", {"1": "HUB_XIN", "3": "HUB_XOUT", "2": "GND", "4": "GND"}, "usb")
R("R4", "R2k7_0402", "HUB_REXT", "GND", "usb")
R("R5", "R10k_0402", "HUB_3V3", "HUB_RST_N", "usb")
C("C17", "C1u_0402", "HUB_RST_N", "GND", "usb")
R("R6", "R10k_0402", "HUB_3V3", "HUB_VBUSM", "usb")
R("R7", "R10k_0402", "HUB_3V3", "HUB_BUSJ", "usb")
R("R8", "R10k_0402", "HUB_3V3", "HUB_OVC_N", "usb")
C("C18", "C10u_0603", "+5V", "GND", "usb")
C("C19", "C100n_0402", "+5V", "GND", "usb")
C("C20", "C4u7_0603", "HUB_3V3", "GND", "usb")
C("C21", "C100n_0402", "HUB_3V3", "GND", "usb")

# ===================== AUDIO =====================
comp("FB1", "FB600_0603", "FB", {"1": "+5V", "2": "+5V_AUD"}, "audio")
comp("U8", "CM108B", "CM108B", {"29": "+5V_AUD", "34": "+5V_AUD", "35": "+5V_AUD", "37": "CODEC_REGV",
                                 "7": "CODEC_REGV", "38": "CODEC_REGV", "41": "AUD_USB_P", "42": "AUD_USB_N",
                                 "8": "CODEC_XI", "9": "CODEC_XO", "10": "GND", "16": "GND", "22": "GND", "23": "GND", "28": "GND",
                                 "27": "CODEC_MICIN", "25": "NC", "26": "CODEC_VREF", "30": "CODEC_LOL", "32": "NC", "31": "NC",
                                 "6": "NC", "18": "NC", "39": "NC", "48": "NC", "40": "NC", "12": "NC", "21": "NC",
                                 "43": "NC", "11": "NC", "13": "NC", "15": "NC", "1": "NC", "2": "NC", "3": "NC", "4": "NC", "5": "NC",
                                 "17": "NC", "19": "NC", "20": "NC", "44": "NC", "45": "NC", "46": "NC", "47": "NC",
                                 "14": "GND", "24": "GND", "33": "GND", "36": "GND"}, "audio")
R("R9", "R1k5_0402", "CODEC_REGV", "AUD_USB_P", "audio")
comp("Y2", "XTAL12M", "XTAL4", {"1": "CODEC_XI", "3": "CODEC_XO", "2": "GND", "4": "GND"}, "audio")
R("R10", "R1M_0402", "CODEC_XI", "CODEC_XO", "audio")
C("C22", "C27p_0402", "CODEC_XI", "GND", "audio")
C("C23", "C27p_0402", "CODEC_XO", "GND", "audio")
C("C24", "C10u_0603", "CODEC_VREF", "GND", "audio")
C("C25", "C10u_0603", "CODEC_REGV", "GND", "audio")
C("C26", "C10u_0603", "+5V_AUD", "GND", "audio")
C("C27", "C100n_0402", "+5V_AUD", "GND", "audio")
C("C28", "C100n_0402", "+5V_AUD", "GND", "audio")
C("C29", "C100n_0402", "CODEC_REGV", "GND", "audio")
# microphone (top-port analog MEMS) with hardware privacy switch
comp("SW4", "SLIDE", "SPDT", {"2": "+3V3A", "1": "MIC_VDD", "3": "MUTE_LED_A"}, "audio")
R("R11", "R10k_0402", "MIC_VDD", "GND", "audio")
R("R12", "R100_0402", "MIC_VDD", "MIC_VDD_F", "audio")
C("C30", "C4u7_0603", "MIC_VDD_F", "GND", "audio")
C("C31", "C100n_0402", "MIC_VDD_F", "GND", "audio")
comp("MK1", "ZTS6216", "ZTS6216", {"4": "MIC_VDD_F", "1": "MIC_OUT", "2": "GND", "3": "GND"}, "audio")
C("C32", "C1u_0402", "MIC_OUT", "CODEC_MICIN", "audio")
LED("D5", "LED_R", "MUTE_LED_A", "MUTE_LED_K", "audio")
R("R13", "R470_0402", "MUTE_LED_K", "GND", "audio")
# speaker amplifier
comp("U9", "PAM8302", "PAM8302", {"6": "+5V", "1": "AMP_SD_N", "3": "AMP_INP", "4": "AMP_INN", "2": "NC",
                                   "5": "SPK_P", "8": "SPK_N", "7": "GND"}, "audio")
R("R14", "R100k_0402", "+5V", "AMP_SD_N", "audio")
C("C33", "C1u_0402", "AMP_SD_N", "GND", "audio")          # soft enable (~100 ms) to avoid pop
C("C34", "C1u_0402", "CODEC_LOL", "AMP_LOL_C", "audio")
R("R15", "R10k_0402", "AMP_LOL_C", "AMP_INP", "audio")
C("C35", "C1u_0402", "AMP_INN_C", "GND", "audio")
R("R16", "R10k_0402", "AMP_INN_C", "AMP_INN", "audio")
C("C36", "C10u_0805", "+5V", "GND", "audio")
C("C37", "C100n_0402", "+5V", "GND", "audio")
comp("J6", "JST_PH2", "CONN2", {"1": "SPK_P", "2": "SPK_N"}, "audio")

# ===================== ZIGBEE =====================
comp("U10", "CP2102N", "CP2102N", {"6": "+3V3A", "7": "+3V3A", "5": "+3V3A", "8": "CP_VBUS",
                                    "3": "ZB_USB_P", "4": "ZB_USB_N", "9": "CP_RST_N",
                                    "21": "ZB_RXD", "20": "ZB_TXD", "19": "ZB_CTS", "18": "ZB_RTS",
                                    "23": "NC", "22": "NC", "24": "NC", "1": "NC", "14": "NC", "13": "NC", "12": "NC", "11": "NC",
                                    "15": "NC", "17": "NC", "10": "NC", "16": "NC", "2": "GND", "25": "GND"}, "zigbee")
R("R17", "R47k_0402", "+5V", "CP_VBUS", "zigbee")
R("R18", "R68k_0402", "CP_VBUS", "GND", "zigbee")
R("R19", "R1k_0402", "+3V3A", "CP_RST_N", "zigbee")
C("C38", "C1u_0402", "+3V3A", "GND", "zigbee")
C("C39", "C100n_0402", "+3V3A", "GND", "zigbee")
# Pin mapping identical to Home Assistant Yellow (so the official Yellow
# Zigbee/Thread firmware images run unmodified):
#   PA05 = module TX, PA06 = module RX, PD02 = CTS in, PC01 = RTS out,
#   PB00 = bootloader button (active low), PB01 = activity LED (active low)
comp("U11", "MGM210P", "MGM210P", {"13": "+3V3A", "14": "+3V3A", "27": "ZB_RST_N", "11": "NC",
                                    "9": "ZB_TXD", "10": "ZB_RXD", "17": "ZB_CTS", "22": "ZB_RTS",
                                    "3": "ZB_BOOT_N", "2": "ZB_LED_N",
                                    "5": "ZB_SWCLK", "6": "ZB_SWDIO", "7": "ZB_SWO",
                                    "4": "NC", "8": "NC", "15": "NC", "16": "NC", "18": "NC", "19": "NC", "21": "NC",
                                    "23": "NC", "24": "NC", "25": "NC", "26": "NC", "29": "GND",
                                    "1": "GND", "12": "GND", "20": "GND", "28": "GND", "30": "GND", "31": "GND"}, "zigbee")
C("C40", "C10u_0603", "+3V3A", "GND", "zigbee")
C("C41", "C100n_0402", "+3V3A", "GND", "zigbee")
R("R20", "R10k_0402", "+3V3A", "ZB_RST_N", "zigbee")
R("R21", "R10k_0402", "+3V3A", "ZB_BOOT_N", "zigbee")
LED("D4", "LED_B", "ZB_LED_A", "ZB_LED_N", "zigbee")
R("R22", "R100_0402", "+3V3A", "ZB_LED_A", "zigbee")
comp("SW3", "TACT", "TACT", {"1": "ZB_BOOT_N", "2": "GND"}, "zigbee")
TP("TP7", "ZB_SWCLK", "zigbee")
TP("TP8", "ZB_SWDIO", "zigbee")
TP("TP9", "ZB_RST_N", "zigbee")
TP("TP10", "ZB_SWO", "zigbee")
TP("TP11", "+3V3A", "zigbee")

# ===================== ETHERNET + SD =====================
comp("J2", "RJ45", "RJ45", {"P2": "ETH0_P", "P3": "ETH0_N", "P4": "ETH1_P", "P7": "ETH1_N",
                             "P5": "ETH2_P", "P6": "ETH2_N", "P8": "ETH3_P", "P9": "ETH3_N",
                             "P1": "ETH_CT_A", "P10": "ETH_CT_B",
                             "11": "+3V3", "12": "ETH_LED1_K", "14": "+3V3", "13": "ETH_LED2_K",
                             "SHIELD0": "GND", "SHIELD1": "GND"}, "eth_sd")
C("C42", "C100n_0402", "ETH_CT_A", "GND", "eth_sd")
C("C43", "C100n_0402", "ETH_CT_B", "GND", "eth_sd")
R("R23", "R470_0402", "ETH_LED1_K", "ETH_LED2_N", "eth_sd")
R("R24", "R470_0402", "ETH_LED2_K", "ETH_LED3_N", "eth_sd")
comp("U13", "TPD4EUSB30", "TPD4EUSB30", {"1": "ETH0_P", "10": "NC", "2": "ETH0_N", "9": "NC",
                                          "4": "ETH1_P", "7": "NC", "5": "ETH1_N", "6": "NC", "3": "GND", "8": "GND"}, "eth_sd")
comp("U14", "TPD4EUSB30", "TPD4EUSB30", {"1": "NC", "10": "ETH2_P", "2": "NC", "9": "ETH2_N",
                                          "4": "ETH3_P", "7": "NC", "5": "ETH3_N", "6": "NC", "3": "GND", "8": "GND"}, "eth_sd")
comp("J5", "USDSOCK", "USDSOCK", {"4": "SD_VDD", "5": "SD_CLK", "3": "SD_CMD", "7": "SD_D0", "8": "SD_D1",
                                   "1": "SD_D2", "2": "SD_D3", "9": "NC", "10": "NC", "6": "GND", "11": "GND"}, "eth_sd")
comp("U12", "RT9742", "RT9742", {"5": "+3V3", "4": "SD_PWR_ON", "2": "GND", "1": "SD_VDD", "3": "NC"}, "eth_sd")
R("R25", "R10k_0402", "+3V3", "SD_PWR_ON", "eth_sd")
C("C44", "C4u7_0603", "SD_VDD", "GND", "eth_sd")
C("C45", "C100n_0402", "SD_VDD", "GND", "eth_sd")
C("C46", "C1u_0402", "+3V3", "GND", "eth_sd")

# ===================== UI / MECH =====================
comp("SW1", "TACT", "TACT", {"1": "PWR_BUT", "2": "GND"}, "ui")
comp("SW2", "TACT", "TACT", {"1": "nRPIBOOT", "2": "GND"}, "ui")
LED("D2", "LED_R", "+3V3", "LED_PWR_K", "ui")
R("R26", "R1k_0402", "LED_PWR_K", "LED_PWR_N", "ui")
LED("D3", "LED_G", "+3V3", "LED_ACT_K", "ui")
R("R27", "R1k_0402", "LED_ACT_K", "LED_ACT_N", "ui")
comp("J7", "JST_SH4", "CONN4MP", {"1": "+5V", "2": "FAN_PWM", "3": "GND", "4": "FAN_TACH", "MP": "GND"}, "ui")
R("R28", "R10k_0402", "+3V3", "FAN_PWM", "ui")
comp("J8", "JST_SH2", "CONN2MP", {"1": "VBAT", "2": "GND", "MP": "GND"}, "ui")
TP("TP1", "DBG_TX", "ui")
TP("TP2", "DBG_RX", "ui")
TP("TP3", "GND", "ui")
TP("TP4", "+5V", "ui")
TP("TP5", "+3V3", "ui")
TP("TP6", "SD_VDD", "ui")
TP("TP12", "HUB_D4_P", "ui")
TP("TP13", "HUB_D4_N", "ui")
for i in range(1, 5):
    comp(f"H{i}", "MH_M3", "MH", {"1": "GND"}, "ui")
for i in range(1, 4):
    comp(f"FID{i}", "FID", "FID", {}, "ui")

# --------------------------------------------------------------------------
# Net classes (used by PCB generator)
# --------------------------------------------------------------------------
DIFF_PAIRS = {
    # name: (P net, N net, class)
    "USB3A_TX": ("USB3A_TX_P", "USB3A_TX_N", "USB3"),
    "USB3A_RX": ("USB3A_RX_P", "USB3A_RX_N", "USB3"),
    "USB3A_D":  ("USB3A_DP", "USB3A_DN", "USB2"),
    "USB2A_D":  ("USB2A_DP", "USB2A_DN", "USB2"),
    "USBC_D":   ("USBC_DP", "USBC_DN", "USB2"),
    "HUB_UP":   ("HUB_UP_P", "HUB_UP_N", "USB2"),
    "AUD_USB":  ("AUD_USB_P", "AUD_USB_N", "USB2"),
    "ZB_USB":   ("ZB_USB_P", "ZB_USB_N", "USB2"),
    "ETH0": ("ETH0_P", "ETH0_N", "ETH"), "ETH1": ("ETH1_P", "ETH1_N", "ETH"),
    "ETH2": ("ETH2_P", "ETH2_N", "ETH"), "ETH3": ("ETH3_P", "ETH3_N", "ETH"),
}
POWER_NETS = {"+5V": 0.8, "+3V3": 0.4, "+3V3A": 0.4, "USB1_VBUS": 0.8, "USB2_VBUS": 0.8,
              "+5V_AUD": 0.3, "SD_VDD": 0.4, "HUB_3V3": 0.3, "SPK_P": 0.5, "SPK_N": 0.5, "CODEC_REGV": 0.3}


def nets():
    """Return {net: [(ref, pin)]} excluding NC."""
    out = {}
    for c in COMPONENTS:
        for pin, net in c["pins"].items():
            if net == "NC":
                continue
            out.setdefault(net, []).append((c["ref"], pin))
    return out


if __name__ == "__main__":
    n = nets()
    print(len(COMPONENTS), "components,", len(n), "nets")
    singles = [k for k, v in n.items() if len(v) < 2]
    print("single-node nets:", singles)
