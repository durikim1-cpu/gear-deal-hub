"""Interactive MacBook Dual-Monitor Dock Compatibility Checker (Topic 1 Consensus)
and 12 Non-Template Hardware Decision Guides (Topic 2 Consensus).
"""

from __future__ import annotations

import html
import json
from typing import Callable

from src.affiliate import BUTTON_DISCLOSURE_EN, BUTTON_DISCLOSURE_KO


def _esc(val: object) -> str:
    return html.escape(str(val))


# --------------------------------------------------------------------------------------
# 12 Original Non-Template Decision Guides (3 Pillars + Price-Free "Budget Setup Picks")
# --------------------------------------------------------------------------------------

GUIDES_EN: list[dict] = [
    {
        "slug": "macbook-m1-m2-m3-dual-monitor-dock-guide",
        "pillar": "MacBook & USB-C Display",
        "pin_headline": "MACBOOK DUAL MONITOR DOCK FIX",
        "title": "Why macOS Mirrors Dual-HDMI Hubs (& How to Run Two Extended Monitors on M1–M4 MacBooks)",
        "summary": "Apple Silicon display engine limits and macOS's lack of DisplayPort MST support cause most multi-HDMI USB-C hubs to mirror screens. Match your exact Mac chip before buying a dock.",
        "reviewed_at": "2026-11-26",
        "tool_cta": "/en/tools/macbook-dock-checker/",
        "intro": (
            "The most common dock return on MacBooks happens when a buyer plugs two HDMI monitors into a generic "
            "USB-C hub and gets two identical mirrored desktops instead of an extended workspace. Two separate limits "
            "govern external monitors on Apple Silicon: first, how many external display pipelines Apple wired into your "
            "specific M-series chip; second, macOS refuses DisplayPort Multi-Stream Transport (MST) daisy-chaining/splitting "
            "over standard USB-C Alt Mode."
        ),
        "matrix_headers": ["MacBook Chip Tier", "Native Lid-Open Limit", "Native Lid-Closed Limit", "Required Dual-Screen Architecture"],
        "matrix_rows": [
            ["M1 / M2 Base (Air & 13\" Pro)", "1 external display", "1 external display", "DisplayLink USB graphics dock (software driver required)"],
            ["M3 Base (Air & 14\" Pro w/ macOS 14.6+)", "1 external display", "2 external displays", "Native Thunderbolt 4 dock (lid closed) OR DisplayLink (lid open)"],
            ["M4 Base / All Pro & Max Chips", "2+ external displays", "2+ external displays", "Native Thunderbolt 4 dock (avoid Windows-only MST HDMI splitters)"],
        ],
        "sections": [
            (
                "Why Windows 'Dual 4K HDMI' USB-C Hubs Mirror on macOS",
                "Most mid-tier multi-monitor USB-C docks use an internal DisplayPort MST splitter chip. Windows 11 treats each downstream HDMI port as an independent display, whereas macOS treats an MST hub as a single sink and clones the signal across both screens. Unless a dock uses true Thunderbolt 4 dual-tunneling (for chips that natively support two displays) or a DisplayLink ASIC with the macOS DisplayLink Manager app, the second screen will only mirror.",
            ),
            (
                "The DisplayLink Trade-Off: HDCP Streaming & Driver Overhead",
                "DisplayLink docks (such as the UGREEN Revodok Pro 209) compress video frames over USB 10Gbps so base M1/M2/M3 MacBooks can run two 4K@60Hz extended monitors even with the laptop lid open. For coding, spreadsheets, browsers, and Slack, latency is barely noticeable. However, while DisplayLink screen recording permission is active in macOS, hardware HDCP DRM blocks protected video streams (Netflix, Apple TV+, Disney+) in Safari and Chrome unless hardware acceleration is toggled off or DisplayLink is disconnected.",
            ),
        ],
        "exclusions": [
            "Skip DisplayLink docks if your primary second-screen workflow is watching HDCP-protected 4K streaming apps or color-grading 10-bit HDR video.",
            "Skip Windows MST docks (like the Anker 575) if your host computer is any macOS laptop—even an M3 Max or M4 Pro.",
            "Skip bus-powered travel hubs for dual monitors; dual 4K output needs dedicated wall power.",
        ],
        "product_ids": [
            "ugreen-revodok-pro-209-dock",
            "caldigit-ts4-thunderbolt4-dock",
            "ugreen-revodok-107-7in1",
            "anker-575-usbc-dock-13in1",
        ],
    },
    {
        "slug": "thunderbolt-4-vs-usb4-nvme-enclosure-mac-thermal-guide",
        "pillar": "MacBook & USB-C Display",
        "pin_headline": "USB4 NVME ENCLOSURE THERMAL GUIDE",
        "title": "USB4 40Gbps NVMe Enclosures for Mac & PC: Controller Chips, Fan Noise, and Sustained Thermal Stability",
        "summary": "40Gbps M.2 enclosures run hot enough to disconnect cheap SSDs during Final Cut or DaVinci exports. Compare active-fan vs heavy passive aluminum enclosures.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "Standard USB 3.2 Gen 2x2 (20Gbps) portable SSDs fall back to 10Gbps (~1,000 MB/s) on every Apple Silicon Mac "
            "because Apple does not implement two-lane USB 3.2 Gen 2x2 on its Thunderbolt controllers. To exceed 2,800 MB/s "
            "on a MacBook or USB4 mini PC, you need a true 40Gbps USB4 / Thunderbolt 4 NVMe enclosure paired with a cool-running PCIe 4.0 M.2 drive."
        ),
        "matrix_headers": ["Enclosure Design", "Idle / Load Acoustics", "Sustained 200GB+ Write Behavior", "Best Host Match"],
        "matrix_rows": [
            ["Fanless Heavy CNC Aluminum (ASM2464PD)", "0 dBA completely silent", "Relies on thermal pad contact to chassis; warm to touch", "Audio/video edit desks & quiet studios"],
            ["Active Micro-Fan Aluminum Chassis", "Audible high-RPM whirr under load", "Keeps controller cooler in warm rooms", "Bulk backups away from open microphones"],
            ["Compact 10Gbps 2230 MagSafe Enclosure", "0 dBA silent", "Capped ~1,000 MB/s; low idle draw", "iPhone ProRes direct capture & travel"],
        ],
        "sections": [
            (
                "Avoid Pairing Power-Hungry DRAM-Heavy Gen4 SSDs in Bus-Powered Enclosures",
                "A 40Gbps bridge controller plus a high-draw desktop NVMe SSD can spike close to the 15W USB-C bus ceiling, causing random unmounts on battery power. Single-sided, efficient TLC drives stay substantially cooler inside sealed aluminum shells than dual-sided workstation drives.",
            ),
            (
                "Why Thermal Pad Placement Matters More Than Peak Benchmark Numbers",
                "If the silicone thermal pad does not bridge the gap between the M.2 controller and the lid, the SSD hits 75°C within 90 seconds and throttles below 10Gbps speeds. Tool-free enclosures with thick machined lids need firm pad compression before closing.",
            ),
        ],
        "exclusions": [
            "Skip active-fan enclosures (like micro-blower 40Gbps shells) if you record vocals or podcasts at the same desk.",
            "Skip 40Gbps enclosures altogether if your host port is USB-C 10Gbps only—you will pay extra heat and weight for zero speed gain.",
        ],
        "product_ids": [
            "satechi-usb4-slim-nvme-pro",
            "orico-m2pjm-usb4-40gbps-enclosure",
            "hagibis-mc100-magsafe-nvme-enclosure",
        ],
    },
    {
        "slug": "iphone-prores-usbc-ssd-recording-setup",
        "pillar": "MacBook & USB-C Display",
        "pin_headline": "IPHONE PRORES USB-C SSD SETUP",
        "title": "Direct ProRes 4K60 Recording on iPhone 15/16 Pro: Sustained Write Floor, Power Draw & MagSafe Mounting",
        "summary": "Dropped frames in Apple ProRes Log happen when a drive's post-SLC sustained write speed dips, not because peak read speed was too low.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "iPhone 15 Pro and 16 Pro unlock external ProRes 4K at 60fps over their 10Gbps USB-C port, provided the connected "
            "storage stays within Apple's 4.5W bus power budget and never drops below ~220–440 MB/s sustained write after the "
            "initial SLC cache fills."
        ),
        "matrix_headers": ["Storage Form Factor", "Cable / Grip Ergonomics", "Pass-Through Charging", "Field Durability"],
        "matrix_rows": [
            ["MagSafe 2230 NVMe Hub w/ PD Pass-Through", "Snaps cleanly to phone back w/ short ribbon cable", "Yes (up to 100W input)", "Requires separate M.2 2230 SSD purchase"],
            ["Ultra-Thin 6mm Magnetic Portable SSD", "Pocket-flat aluminum, minimal rig bulk", "No pass-through port on drive", "Pre-built sealed drive, verify sustained TLC write"],
            ["Rugged IP65 Rubberized 10Gbps SSD", "Needs cage clamp; heavier on gimbals", "No pass-through port", "3m drop + rain/dust resistance"],
        ],
        "sections": [
            (
                "Peak 2,000 MB/s Stickers Mean Nothing on a 10Gbps iPhone Port",
                "Both iPhone 15 Pro and 16 Pro max out at USB 3.2 Gen 2 (10Gbps). Paying extra for a 20Gbps USB 3.2 Gen 2x2 drive will still negotiate at 10Gbps on iPhone and Mac. What prevents dropped-frame stops mid-take is sustained post-cache write stability and staying under the 4.5W port limit.",
            ),
        ],
        "exclusions": [
            "Skip non-Pro iPhone 15 / 16 base models for 10Gbps external workflows—their USB-C port runs at USB 2.0 (480Mbps).",
            "Skip thick MagSafe silicone cases without a magnetic ring if relying on magnetic SSD attachment while walking.",
        ],
        "product_ids": [
            "hagibis-mc100-magsafe-nvme-enclosure",
            "lexar-sl500-2tb-magnetic-ssd",
            "samsung-t7-shield-2tb",
        ],
    },
    {
        "slug": "clamshell-macbook-vertical-stand-airflow-guide",
        "pillar": "MacBook & USB-C Display",
        "pin_headline": "CLAMSHELL MACBOOK DESK AIRFLOW",
        "title": "Clamshell Desk Setup for MacBook Air & Pro: Hinge Vents, Cable Strain & Vertical Stand Sizing",
        "summary": "Parking an M3 MacBook Air in clamshell mode unlocks dual native monitors—if your vertical stand doesn't choke hinge exhaust or scratch anodized edges.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "Running a laptop closed beside an external monitor reclaims half of a shallow desk, and on M3 MacBook Air models "
            "it is the official trigger that unlocks a second native external display. Getting clamshell ergonomics right comes "
            "down to hinge orientation, silicone slot grip, and a single Thunderbolt cable with clean strain relief."
        ),
        "matrix_headers": ["Setup Component", "Critical Physical Check", "Failure Mode If Ignored", "Recommended Spec"],
        "matrix_rows": [
            ["Vertical Aluminum Stand", "Tool-free thumbscrew width 12–26mm + full silicone liner", "Metal-on-metal edge scuffs or tipping w/ stiff TB4 cable", "Weighted dual-slot anodized aluminum"],
            ["Host Power & Video", "macOS requires AC power connected for closed-display mode", "Monitors sleep immediately when lid closes", "85W–98W PD dock or dedicated GaN port"],
            ["Task Lighting", "Asymmetric optical beam cleared past top webcam", "Screen glare & washed-out blacks", "Ra95 asymmetric light bar w/ wireless puck"],
        ],
        "sections": [
            (
                "Hinge-Up vs Hinge-Down Orientation on Fanless vs Active-Cooled Laptops",
                "MacBook Pro 14\" and 16\" models vent warm air along the rear hinge crease; placing them hinge-up in a vertical cradle lets heat rise unimpeded instead of baking into the desk surface. Fanless MacBook Air chassis dissipate heat through the bottom aluminum plate, so leaving breathing room between dual slots avoids heat soak.",
            ),
        ],
        "exclusions": [
            "Skip fixed-width plastic cradles if you switch between a bare MacBook Air (11.3mm) and a cased work laptop.",
            "Skip clamshell mode during heavy multi-hour 3D rendering on fanless MacBook Airs if ambient room temps are high.",
        ],
        "product_ids": [
            "ugreen-vertical-laptop-stand-dual",
            "caldigit-ts4-thunderbolt4-dock",
            "xiaomi-mijia-monitor-lightbar-1s",
        ],
    },
    {
        "slug": "multi-port-gan-charger-renegotiation-drop-guide",
        "pillar": "US Desk Power & GaN Charging",
        "pin_headline": "100W-160W GAN CHARGER PORT GUIDE",
        "title": "Multi-Port GaN Chargers (100W–160W): Understanding the 1-Second Power Drop & Real Port Allocation",
        "summary": "Why plugging in your phone briefly disconnects a USB-C monitor or bus-powered hub—and how to pick the right 100W vs 140W/160W US-plug GaN charger.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "Nearly every multi-port USB-C PD GaN charger dynamically reallocates wattage across shared buck-boost circuits "
            "whenever a cable is inserted or unplugged. During that ~1-second PD handshake reset, laptops on battery never "
            "blink—but batteryless devices like Mini PCs, Stream Decks, or bus-powered USB-C hubs will reboot."
        ),
        "matrix_headers": ["Wattage Class", "Single-Port Ceiling", "Typical 2-Laptop Split", "US Wall Outlet Stability"],
        "matrix_rows": [
            ["Compact 100W 3-Port (PD 3.0)", "100W (drives 14\" MBP full speed)", "65W + 30W", "Lighter (~170–200g), stays Seated in worn duplex outlets"],
            ["Desktop/Wall 100W 4-Port", "100W single USB-C", "65W + 30W (or 45W + 30W + 20W)", "300g+ brick—better in power strips than loose vertical wall sockets"],
            ["140W–160W PD 3.1 4-Port", "140W EPR (16\" MBP w/ MagSafe 3)", "100W + 45W / 65W + 65W", "Heavy brick; pair with desktop AC cord or flat strip"],
        ],
        "sections": [
            (
                "PD 3.0 (100W) vs PD 3.1 EPR (140W): Do Not Overspend Without an EPR Cable",
                "Reaching 140W on a 16-inch MacBook Pro often requires Apple's USB-C to MagSafe 3 cable (or a 240W EPR USB-C cable on M3/M4 16-inch models). Standard 100W 5A e-marked USB-C cables physically cap charging at 100W regardless of whether your charger says 140W or 160W.",
            ),
        ],
        "exclusions": [
            "Never power a batteryless Mini PC from a shared multi-port GaN charger where phones get plugged and unplugged.",
            "Skip heavy 300g+ prong bricks for worn airplane seat outlets—use a lighter 3-port compact GaN or grounded desktop station.",
        ],
        "product_ids": [
            "anker-prime-100w-a2688",
            "iniu-100w-3port-gan-i611",
            "ugreen-nexode-100w-4port",
            "ugreen-nexode-pro-160w",
        ],
    },
    {
        "slug": "faa-tsa-100wh-laptop-powerbank-carry-on-guide",
        "pillar": "US Desk Power & GaN Charging",
        "pin_headline": "TSA 100WH LAPTOP POWER BANK GUIDE",
        "title": "TSA & FAA 100Wh Carry-On Power Banks: Real Wh Ratings, Sustained 100W–140W Output & Bag Fit",
        "summary": "Airlines regulate watt-hours (Wh), not mAh. Every vetted 20,000–25,000mAh laptop bank below sits safely under the 100Wh carry-on ceiling—with very different shapes.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "FAA and TSA rules permit spare lithium-ion power banks up to 100 watt-hours (Wh) in carry-on luggage without "
            "airline pre-approval (checked bags are strictly prohibited). Because nominal cell voltage is ~3.6V–3.7V, a "
            "20,000mAh pack equals ~72Wh and a 25,000mAh pack equals ~90Wh—both legal for carry-on provided the Wh label on "
            "the casing is legible."
        ),
        "matrix_headers": ["Form Factor", "Capacity (Wh)", "Sustained Laptop Output", "Best Carry Scenario"],
        "matrix_rows": [
            ["18mm Flat 'Blade' Slab", "~72Wh (20,000mAh)", "100W single USB-C", "Slides flat beside laptop in slim briefcases"],
            ["Columnar High-Rate Pack w/ OLED", "72Wh–90Wh (20k–25k mAh)", "100W–140W PD 3.1 + fast 90–110W recharge", "Tech backpacks needing two high-wattage ports"],
            ["Compact 10,000mAh 100W Bar", "~36Wh (10,000mAh)", "Short-burst laptop top-up / fast phone charge", "Jacket pocket & short domestic hops"],
        ],
        "sections": [
            (
                "Why Usable Wh at the Laptop Is ~75–82% of Printed Cell Capacity",
                "Stepping 3.7V battery cells up to 20V or 28V USB-C PD incurs DC-DC conversion heat on both ends. Expect a 72Wh pack to add roughly 75–85% charge to a MacBook Air 13\" (~52.6Wh battery), not 135%.",
            ),
        ],
        "exclusions": [
            "Never place any lithium power bank in gate-checked or checked luggage.",
            "Skip transparent acrylic showcase shells (like Shargeek 170) if your bag has loose metal keys that scratch glossy plastic.",
        ],
        "product_ids": [
            "anker-prime-20000-200w",
            "baseus-blade-hd-100w",
            "anker-737-powercore-24k-140w",
            "cuktech-20-powerbank-25000-210w",
        ],
    },
    {
        "slug": "clean-desk-charging-station-vs-wall-wart-guide",
        "pillar": "US Desk Power & GaN Charging",
        "pin_headline": "CLEAN DESK CHARGING STATION SETUP",
        "title": "Desktop Charging Stations vs Prong Wall Bricks: US Cord Routing, Retractable Cables & Qi2 Heat",
        "summary": "Moving AC-to-DC conversion onto your desk with a figure-8 cord stops under-desk brick sag—provided you understand retractable cable wear and Qi2 thermal limits.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "Wall-wart GaN chargers force three or four stiff USB-C cables to run all the way from an under-desk power strip "
            "up to your tabletop. Desktop charging stations bring one slim AC power cord to the back edge of the desk and "
            "keep short device leads within arm's reach."
        ),
        "matrix_headers": ["Charging Style", "Cable Clutter Impact", "Wireless / Magnetic Pad", "Long-Term Wear Point"],
        "matrix_rows": [
            ["5-in-1 Station w/ Retractable Cable + Qi2", "Eliminates loose phone cable on desk", "15W Qi2 magnetic tilt pad", "Internal retracting reel mechanism cannot be user-replaced"],
            ["4-Port High-Output Brick + Own Cables", "Requires separate cable clips", "None (wired efficiency only)", "Standard replaceable e-marked USB-C cables"],
            ["Qi2 10k Kickstand Pack on Desk", "Doubles as grab-and-go battery", "15W Qi2 certified", "Slower wired port (27W) for phones only"],
        ],
        "sections": [
            (
                "Qi2 15W Convenience vs Battery Heat",
                "Qi2 brings Apple's magnetic coil alignment open standard to third-party stands for steady 15W wireless charging, but inductive charging still warms phones noticeably more than a 20W wired USB-C lead—use wired ports when fast-topping before heading out.",
            ),
        ],
        "exclusions": [
            "Skip stations with built-in non-replaceable retractable cables if multiple family members yank cables at sharp side angles.",
            "Confirm US 120V NEMA plug variant when ordering cross-border—EU/KR round-pin plugs need adapters that wobble.",
        ],
        "product_ids": [
            "baseus-nomos-140w-5in1",
            "cuktech-15-gan-140w-charger",
            "anker-maggo-10k-qi2-a1654",
        ],
    },
    {
        "slug": "monitor-light-bar-curved-screen-glare-guide",
        "pillar": "US Desk Power & GaN Charging",
        "pin_headline": "MONITOR LIGHT BAR & WEBCAM FIT",
        "title": "Monitor Light Bars on Flat & Curved Displays: Asymmetric Optics, Bezel Clamps & Webcam Stacking",
        "summary": "A true asymmetric light bar illuminates your keyboard without washing out OLED/IPS contrast—if the counterweight clamp fits your monitor's rear hump.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "Desk lamps placed beside an ultrawide or dual-monitor rig bounce specular glare off matte coatings. Monitor "
            "light bars clip onto the top bezel and project an angled forward cut-off beam onto the desk surface while "
            "keeping zero direct light on the LCD/OLED panel."
        ),
        "matrix_headers": ["Control & Power Design", "Curved Monitor Fit", "Desk Space Saved", "Webcam Coexistence"],
        "matrix_rows": [
            ["Wireless 2.4GHz Puck + Front/Rear RGB", "Fits flat & gentle curves (check 1000R steepness)", "Zero cable clutter; puck sits beside mouse", "Flat top edge allows light 1/4\" webcam rest"],
            ["Wireless Puck Asymmetric Ra95 Bar", "Best on flat & mild 1800R–1500R bezels", "5V 2A USB-C power (wall/hub recommended)", "Clean minimal profile"],
            ["On-Bar Capacitive Touch Light Bar", "Flat panels & slim bezels", "No desk puck needed; runs off 5V 1A monitor USB", "Touching bar can nudge ultra-thin monitors"],
        ],
        "sections": [
            (
                "Check Top Bezel Lip Depth & Rear Cooling Humps Before Buying",
                "Gaming monitors with thick triangular rear RGB spines (40mm+ deep) or frameless OLED panels thinner than 5mm can cause standard gravity clamps to tilt forward onto the display glass. Checking return flexibility matters whenever your monitor back isn't flat.",
            ),
        ],
        "exclusions": [
            "Skip straight aluminum light bars on aggressive 800R/1000R curved ultrawides unless the manufacturer specifies curved-clamp clearance.",
            "Avoid powering high-brightness dual-light (front + RGB bias) bars from an unpowered 500mA keyboard USB pass-through port.",
        ],
        "product_ids": [
            "yeelight-screen-bar-pro-ra95",
            "xiaomi-mijia-monitor-lightbar-1s",
            "baseus-i-wok2-touch-lightbar",
            "insta360-link-2c-4k-webcam",
        ],
    },
    {
        "slug": "hall-effect-vs-tmr-pc-switch-controller-guide",
        "pillar": "Controllers & Portable Storage",
        "pin_headline": "HALL EFFECT VS TMR CONTROLLER GUIDE",
        "title": "Hall Effect vs TMR Wireless Controllers for PC, Switch & Mobile: Stick Drift, 1000Hz Polling & Trigger Locks",
        "summary": "Contactless magnetic sensors ended potentiometer stick drift—now choose between simple 1000Hz PC pads, Switch wake docks, and dual-mode FPS trigger locks.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "First-party console pads still rely on carbon-film potentiometers that wear down and drift. Third-party Hall Effect "
            "and Tunnel Magnetoresistance (TMR) controllers read thumbstick position magnetically without physical wiper contact, "
            "while adding 1000Hz 2.4GHz wireless dongles and remappable extra bumpers/paddles."
        ),
        "matrix_headers": ["Controller Type", "Stick & Trigger Tech", "Platform Support", "Standout Advantage"],
        "matrix_rows": [
            ["Lightweight 2.4GHz / BT PC Pad", "Hall sticks + analog Hall triggers", "Windows PC & Android (no Switch gyro)", "1000Hz wireless dongle + extra top L4/R4 bumpers"],
            ["TMR Docked Multi-Platform Pad", "TMR sticks + mechanical hair-trigger lock", "PC, Switch, iOS, Android", "Instant switch between racing analog & shooter click triggers"],
            ["Switch/PC Charging-Dock Classic", "Hall Effect sticks + rear P1/P2 paddles", "Nintendo Switch (wake + gyro) & PC", "Drop-in magnetic charging dock stores 2.4G receiver"],
            ["Telescopic USB-C Mobile Grip", "Hall sticks + 3.5mm audio + PD pass-through", "iPhone 15/16 & USB-C Android", "Zero Bluetooth audio lag via pivoting USB-C plug"],
        ],
        "sections": [
            (
                "Hall Effect vs TMR: What Actually Changed",
                "TMR (Tunnel Magnetoresistance) sensors consume less current on wireless battery power and allow finer factory linearity calibration than first-generation Hall modules, while physical micro-switch trigger stops remove the mushy bottom-out travel in shooters.",
            ),
        ],
        "exclusions": [
            "None of these PC/Switch wireless pads work natively on Xbox Series X|S or PS5 consoles without licensed Xbox/PlayStation security chips.",
            "Double-check the exact 8BitDo sub-model: the 'Ultimate 2C Wireless' is for PC/Android and does NOT connect to Nintendo Switch.",
        ],
        "product_ids": [
            "8bitdo-ultimate-2c-wireless",
            "gamesir-cyclone-2-tmr-dock",
            "8bitdo-ultimate-bluetooth-dock",
            "gamesir-g8-galileo-usbc-mobile",
        ],
    },
    {
        "slug": "portable-ssd-sustained-write-counterfeit-guide",
        "pillar": "Controllers & Portable Storage",
        "pin_headline": "PORTABLE SSD BUYING & FAKE CHECK",
        "title": "Portable SSD Buying Guide (10Gbps vs 20Gbps): DRAM Cache, Mac Speed Caps & Avoiding Counterfeit Flash",
        "summary": "Why storage is the #1 category where verified domestic fulfillment beats unvetted marketplace listings—plus how to avoid the 20Gbps USB 3.2 Gen 2x2 trap on Mac.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "External SSDs look identical from the outside whether they hold genuine TLC NAND with DRAM cache or relabeled "
            "microSD controller boards that corrupt files past 64GB. Storage is the single hardware category where seller "
            "provenance and official manufacturer tool verification matter more than chasing marginal cross-border discounts."
        ),
        "matrix_headers": ["Drive Architecture", "USB Interface", "Real Speed on Mac vs Windows 2x2 Port", "Best Workload"],
        "matrix_rows": [
            ["10Gbps w/ Dedicated DRAM Cache", "USB 3.2 Gen 2 (10Gbps)", "~1,000 MB/s on both Mac & Windows", "Steam libraries, VM images, random small-file I/O"],
            ["Rugged IP65 10Gbps Shielded SSD", "USB 3.2 Gen 2 (10Gbps)", "~1,000 MB/s on both Mac & Windows", "Outdoor photo/video backups & travel bags"],
            ["20Gbps Gen 2x2 Portable SSD", "USB 3.2 Gen 2x2 (20Gbps)", "~1,000 MB/s on Mac · up to ~2,000 MB/s on Windows 2x2", "Windows desktops/motherboards with native 20Gbps port"],
        ],
        "sections": [
            (
                "30-Second Counterfeit Verification After Delivery",
                "Immediately connect any new Samsung, Crucial, SK hynix, or Lexar drive to the brand's official utility (such as Samsung Magician) and run a full sequential write test past 100GB. Fake drives fail firmware authentication immediately.",
            ),
        ],
        "exclusions": [
            "Skip unverified third-party marketplace sellers for any flash storage product—always check seller identity and manufacturer warranty coverage.",
            "Skip 20Gbps Gen 2x2 models if you exclusively use MacBooks; choose a 10Gbps DRAM drive or jump straight to a 40Gbps USB4 enclosure.",
        ],
        "product_ids": [
            "sk-hynix-beetle-x31-1tb",
            "crucial-x9-pro-2tb-ssd",
            "samsung-t7-shield-2tb",
            "samsung-t9-2tb-20gbps",
        ],
    },
    {
        "slug": "untreated-room-usb-xlr-dynamic-mic-setup",
        "pillar": "Controllers & Portable Storage",
        "pin_headline": "DYNAMIC USB/XLR MIC ROOM GUIDE",
        "title": "USB/XLR Dynamic Microphones for Untreated Rooms: Rejecting Mechanical Keyboard Clack Without Acoustic Foam",
        "summary": "Condenser mics pick up every HVAC hum and keyboard switch in a bare bedroom. Hybrid USB-C/XLR dynamic mics isolate close speech now and upgrade cleanly later.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "Popular desktop condenser microphones have wide sensitivity that captures room echo, mouse clicks, and computer "
            "fans from three feet away. A cardioid dynamic capsule requires speaking 2 to 4 inches from the grille, naturally "
            "dropping background room noise by 10–15 dB before any AI noise filter touches your voice."
        ),
        "matrix_headers": ["Mic Feature", "Why It Matters on a Shared Desk", "USB-C Mode", "Future XLR Upgrade Path"],
        "matrix_rows": [
            ["Dual USB-C + XLR Dynamic Capsule", "Start plug-and-play today; add an audio interface later without rebuying", "Direct to Mac/PC w/ 3.5mm zero-latency monitoring", "Standard balanced 3-pin XLR (no 48V phantom needed)"],
            ["Capacitive Top Mute + Physical Gain", "Mutes coughs silently without mechanical button thump", "Active in USB mode", "Muted via audio interface in XLR mode"],
            ["Integrated Shock Mount & Threading", "Absorbs desk bumps from typing", "Fits 3/8\" & 5/8\" low-profile boom arms", "Same mount works in both modes"],
        ],
        "sections": [
            (
                "Plan for a Low-Profile Boom Arm: Dynamic Mics Must Sit Close",
                "Leaving a dynamic microphone down on its short included desk stand 16 inches below your mouth forces you to crank gain to 95%, bringing preamp hiss right back. Budget desk clamp space to bring the capsule within a fist's width of your chin.",
            ),
        ],
        "exclusions": [
            "Skip dynamic mics if you want to sit two feet back and capture a multi-person conference table—cardioid dynamics drop off steeply off-axis.",
            "Remember that on-body USB mute buttons, RGB rings, and 3.5mm headphone jacks turn off when connected solely via an analog XLR cable.",
        ],
        "product_ids": [
            "fifine-am8-dynamic-mic",
            "fifine-k688-podcast-dynamic-mic",
            "maono-pd200x-usb-xlr-mic",
        ],
    },
    {
        "slug": "budget-setup-picks-practical-desk-upgrades",
        "pillar": "Budget Setup Picks",
        "pin_headline": "BUDGET SETUP PICKS: VETTED UPGRADES",
        "title": "Budget Setup Picks: 6 Practical Desk & Everyday Carry Upgrades With Honest Trade-Offs",
        "summary": "Price-free curated shortlist of practical everyday hardware upgrades—vetted for real-world caveats, compatibility boundaries, and domestic vs direct-import trade-offs.",
        "reviewed_at": "2026-11-26",
        "intro": (
            "Small peripheral upgrades often deliver a bigger daily quality-of-life jump than CPU upgrades—if you avoid "
            "accessory traps, proprietary software lock-in, and mismatched connectors. Every pick in this Budget Setup Picks "
            "collection clears our standalone-hardware gatekeeper and lists its biggest day-to-day caveat upfront."
        ),
        "matrix_headers": ["Upgrade Category", "Core Hardware Gain", "Main Compromise to Accept", "When Domestic US Beats Direct Import"],
        "matrix_rows": [
            ["Hall-Effect 1000Hz Wireless Pad", "Zero potentiometer stick drift + 2.4G dongle", "PC/Android only (no Switch/console support)", "Fast stick/bumper QC check & easy domestic return"],
            ["Compact 100W 3-Port GaN Brick", "Replaces separate laptop + phone bricks under 200g", "1-second renegotiation pause when adding cables", "Verified US NEMA prongs & safety listing"],
            ["Ultra-Slim ZMK Scissor Keyboard", "8-month battery + browser-based key remapping", "No backlight in dark rooms", "Quick key-feel trial if switching from mechanical"],
            ["75% Pre-Lubed Gasket Keyboard", "Deep dampened typing sound out of the box", "Windows-only driver software (no QMK/VIA)", "Faster arrival vs switch-variant selection direct"],
            ["54g PAW3395 Wireless Mouse", "Flagship sensor tracking without honeycomb holes", "Web/light software; check grip size for large hands", "Direct brand store promos vs domestic exchange"],
            ["USB-C DSP Alloy In-Ear Monitors", "Plug-and-play mic + app EQ without 3.5mm dongle", "Brass nozzle condensation needs periodic wiping", "Quick replacement if channel imbalance occurs"],
        ],
        "sections": [
            (
                "How We Maintain Price-Free Objectivity in Budget Setup Picks",
                "Retailer promos, coupons, and cross-border import fees shift daily. Rather than printing stale dollar stickers that go wrong overnight, we focus on permanent hardware engineering traits and let you compare live checkout totals directly on Amazon US and AliExpress.",
            ),
        ],
        "exclusions": [
            "Skip ultra-slim non-backlit scissor keyboards if you type in unlit rooms without a monitor light bar.",
            "Skip compact 54g symmetrical mice if you use a full palm grip with 20cm+ hands.",
        ],
        "product_ids": [
            "8bitdo-ultimate-2c-wireless",
            "iniu-100w-3port-gan-i611",
            "keychron-b1-pro-scissor",
            "aula-f75-wireless-keyboard",
            "vxe-dragonfly-r1-pro-max",
            "moondrop-chu-2-dsp-usbc",
        ],
    },
]


# --------------------------------------------------------------------------------------
# MacBook Dual-Monitor Dock Compatibility Checker (Topic 1 Unanimous Consensus Tool)
# --------------------------------------------------------------------------------------

DOCK_TOOL_JS = r"""
(() => {
  const root = document.querySelector('[data-dock-tool]');
  if (!root) return;
  const lang = root.dataset.lang || 'ko';
  const DATA = JSON.parse(root.querySelector('[data-dock-json]').textContent);
  const chipSel = root.querySelector('[name="mac_chip"]');
  const monSel = root.querySelector('[name="monitors"]');
  const lidSel = root.querySelector('[name="lid_mode"]');
  const hdcpSel = root.querySelector('[name="hdcp_need"]');
  const out = root.querySelector('[data-dock-result]');

  function track(evName, detail) {
    try {
      window.dispatchEvent(new CustomEvent('gch:funnel', { detail: Object.assign({ event: evName, lang }, detail || {}) }));
    } catch (e) {}
  }

  function evaluate() {
    const chip = chipSel.value;
    const mons = monSel.value;
    const lid = lidSel.value;
    const hdcp = hdcpSel.value;

    let status = 'ok'; // ok | warn | hold
    let badge = '';
    let headline = '';
    let reason = '';
    let picks = [];

    if (chip === 'other_unverified') {
      status = 'hold';
      badge = DATA.t.hold_badge;
      headline = DATA.t.hold_head;
      reason = DATA.t.hold_body;
      picks = [];
    } else if (chip === 'windows_usb4') {
      status = 'ok';
      badge = DATA.t.win_badge;
      headline = mons === '2' ? DATA.t.win_dual_head : DATA.t.win_single_head;
      reason = DATA.t.win_body;
      picks = mons === '2' ? ['anker-575-usbc-dock-13in1', 'ugreen-revodok-pro-209-dock'] : ['ugreen-revodok-107-7in1', 'anker-575-usbc-dock-13in1'];
    } else if (mons === '1') {
      status = 'ok';
      badge = DATA.t.native_ok_badge;
      headline = DATA.t.single_head;
      reason = DATA.t.single_body;
      picks = ['ugreen-revodok-107-7in1', 'caldigit-ts4-thunderbolt4-dock'];
    } else if (chip === 'm1_m2_base') {
      if (hdcp === 'yes') {
        status = 'warn';
        badge = DATA.t.hdcp_warn_badge;
        headline = DATA.t.m12_hdcp_head;
        reason = DATA.t.m12_hdcp_body;
        picks = ['ugreen-revodok-107-7in1', 'ugreen-revodok-pro-209-dock'];
      } else {
        status = 'ok';
        badge = DATA.t.dl_req_badge;
        headline = DATA.t.m12_dl_head;
        reason = DATA.t.m12_dl_body;
        picks = ['ugreen-revodok-pro-209-dock'];
      }
    } else if (chip === 'm3_base') {
      if (lid === 'closed') {
        status = 'ok';
        badge = DATA.t.native_clamshell_badge;
        headline = DATA.t.m3_closed_head;
        reason = DATA.t.m3_closed_body;
        picks = ['caldigit-ts4-thunderbolt4-dock', 'ugreen-vertical-laptop-stand-dual'];
      } else if (hdcp === 'yes') {
        status = 'warn';
        badge = DATA.t.hdcp_warn_badge;
        headline = DATA.t.m3_open_hdcp_head;
        reason = DATA.t.m3_open_hdcp_body;
        picks = ['caldigit-ts4-thunderbolt4-dock', 'ugreen-revodok-pro-209-dock'];
      } else {
        status = 'ok';
        badge = DATA.t.dl_req_badge;
        headline = DATA.t.m3_open_dl_head;
        reason = DATA.t.m3_open_dl_body;
        picks = ['ugreen-revodok-pro-209-dock', 'caldigit-ts4-thunderbolt4-dock'];
      }
    } else if (chip === 'm4_base' || chip === 'pro_max') {
      status = 'ok';
      badge = DATA.t.native_dual_badge;
      headline = DATA.t.promax_head;
      reason = DATA.t.promax_body;
      picks = ['caldigit-ts4-thunderbolt4-dock', 'ugreen-vertical-laptop-stand-dual'];
    }

    const cardsHtml = picks.map(id => DATA.cards[id] || '').join('');
    const holdChecklist = status === 'hold' ? `<ul class="tool-check">${DATA.t.hold_checks.map(x => `<li>${x}</li>`).join('')}</ul>` : '';
    const mstWarn = (chip !== 'windows_usb4' && chip !== 'other_unverified' && mons === '2')
      ? `<div class="tool-alert"><strong>${DATA.t.mst_warn_title}</strong><span>${DATA.t.mst_warn_desc}</span></div>`
      : '';

    out.innerHTML = `
      <div class="verdict-box is-${status}">
        <span class="v-badge">${badge}</span>
        <h2>${headline}</h2>
        <p>${reason}</p>
        ${holdChecklist}
        ${mstWarn}
      </div>
      ${cardsHtml ? `<div class="tool-picks"><h3>${DATA.t.rec_heading}</h3><div class="tool-grid">${cardsHtml}</div><p class="btn-disc">${DATA.t.btn_disc}</p></div>` : ''}
    `;

    // Re-apply dynamic channel tracking on newly injected store links
    if (window.__gchApplyAttribution) window.__gchApplyAttribution(out);
    track('check_complete', { chip, mons, lid, hdcp, status });
  }

  [chipSel, monSel, lidSel, hdcpSel].forEach(el => el.addEventListener('change', evaluate));
  track('tool_view', { tool: 'macbook-dock-checker' });
  evaluate();
})();
"""


def _render_tool_product_card(it: dict, lang: str, detail_prefix: str, slug_fn: Callable[[str], str], up: str = "../../../") -> str:
    loc = it[lang]
    links = it["affiliate_links"]
    slug = slug_fn(it["id"])
    dom_url = links["coupang"] if lang == "ko" else links["amazon"]
    dom_cls = "btn-coupang" if lang == "ko" else "btn-amazon"
    dom_lbl = "쿠팡 실시간 가격·재고 확인" if lang == "ko" else "Check Price on Amazon"
    ali_lbl = "알리 직구 조건 확인" if lang == "ko" else "Check AliExpress"
    detail_lbl = "상세 스펙·단점 보기" if lang == "ko" else "Specs & Caveats"
    con_lbl = "주의할 단점:" if lang == "ko" else "Caveat:"
    alt_txt = f"{it['brand']} {it['model']}"
    return (
        f'<article class="panel tool-card">'
        f'<div class="tc-top">'
        f'<a class="tc-thumb" href="{detail_prefix}{slug}/" tabindex="-1">'
        f'<img src="{up}assets/products/{slug}.webp" alt="{_esc(alt_txt)}" width="80" height="80" loading="lazy" decoding="async">'
        f'</a>'
        f'<div class="tc-meta"><span class="tag">{_esc(it["brand"])} · {_esc(it["model"])}</span>'
        f'<h4><a href="{detail_prefix}{slug}/">{_esc(loc["title"])}</a></h4></div>'
        f'</div>'
        f'<p class="tc-sum">{_esc(loc["summary"])}</p>'
        f'<p class="tc-con"><strong>{con_lbl}</strong> {_esc(loc["cons"][0])}</p>'
        f'<div class="actions">'
        f'<a class="btn {dom_cls}" data-aff="dom" data-store="{"coupang" if lang == "ko" else "amazon"}" href="{_esc(dom_url)}" target="_blank" rel="nofollow sponsored noopener">{dom_lbl}</a>'
        f'<a class="btn btn-ali" data-aff="ali" data-store="aliexpress" href="{_esc(links["aliexpress"])}" target="_blank" rel="nofollow sponsored noopener">{ali_lbl}</a>'
        f'</div>'
        f'<a class="tc-more" href="{detail_prefix}{slug}/">{detail_lbl} →</a>'
        f'</article>'
    )


def render_dock_checker_page(
    *,
    lang: str,
    items_by_id: dict[str, dict],
    cfg: dict,
    head_fn: Callable[..., str],
    legal_fn: Callable[[str], str],
    header_fn: Callable[[str, str, dict, str], str],
    footer_fn: Callable[[str, str, dict], str],
    slug_fn: Callable[[str], str],
) -> str:
    up = "../../../"
    other = "en" if lang == "ko" else "ko"
    path = f"/{lang}/tools/macbook-dock-checker/"
    alternates = {
        "ko": "/ko/tools/macbook-dock-checker/",
        "en": "/en/tools/macbook-dock-checker/",
    }
    needed_ids = [
        "ugreen-revodok-pro-209-dock",
        "caldigit-ts4-thunderbolt4-dock",
        "ugreen-revodok-107-7in1",
        "anker-575-usbc-dock-13in1",
        "ugreen-vertical-laptop-stand-dual",
    ]
    cards = {
        pid: _render_tool_product_card(items_by_id[pid], lang, "../../p/", slug_fn)
        for pid in needed_ids
        if pid in items_by_id
    }

    if lang == "ko":
        title = f"맥북 모델·칩별 듀얼모니터 독 호환 판별기 (M1·M2·M3·M4) | {cfg['site']['brand_name']}"
        desc = "내 맥북 에어·프로 칩셋과 클램쉘 여부, 넷플릭스(HDCP) 사용 여부에 맞춰 화면 복제(미러링) 실패 없는 도킹스테이션 구성을 즉시 판별합니다."
        h1 = "맥북 모델·칩별 듀얼모니터 독 호환 판별기"
        lead = "맥북에서 '듀얼 HDMI 허브'를 샀다가 두 모니터에 똑같은 화면만 복제되어 반품하는 사고를 막기 위한 공식 사양 교차 검증 도구입니다. Apple 외부 디스플레이 사양과 DisplayLink·Thunderbolt 4 작동 조건이 확인된 조합만 추천하며, 불확실한 특수 구성은 억지 추천 대신 '판정 유보'로 표시합니다."
        labels = ("1. 노트북 모델 · 칩셋", "2. 연결할 외부 모니터 수", "3. 노트북 덮개(클램쉘) 상태", "4. OTT 스트리밍(넷플릭스·티빙 등 HDCP) 상시 재생")
        chip_opts = [
            ("m1_m2_base", "맥북 에어 M1 / M2 (13·15인치) 및 맥북 프로 13인치 (M1/M2 기본칩)"),
            ("m3_base", "맥북 에어 M3 (13·15인치) 및 맥북 프로 14인치 (M3 기본칩, macOS 14.6+)"),
            ("m4_base", "맥북 프로 14인치 / 에어 (M4 기본칩)"),
            ("pro_max", "맥북 프로 14·16인치 (M1 / M2 / M3 / M4 Pro · Max 칩)"),
            ("windows_usb4", "윈도우 11 노트북 (USB4 / 썬더볼트4 지원)"),
            ("other_unverified", "구형 인텔 맥 / 리눅스 / 고주사율 4K 144Hz DSC·데이지체인 특수 구성"),
        ]
        mon_opts = [("2", "외부 모니터 2대 독립 확장 (듀얼 모니터)"), ("1", "외부 모니터 1대 연결 (단일 4K/울트라와이드)")]
        lid_opts = [("open", "노트북 화면을 열어두고 함께 사용"), ("closed", "노트북 덮개를 닫고 사용 (클램쉘 모드 + 전원 연결)")]
        hdcp_opts = [("no", "코딩·문서·웹·업무 위주 (OTT 재생 시 독 분리 가능)"), ("yes", "넷플릭스·디즈니+ 등 DRM 영상 상시 재생 필수")]
        t_data = {
            "hold_badge": "판정 유보 · 공식 사양 개별 확인 필요",
            "hold_head": "이 구성은 자동 단정 추천을 제공하지 않습니다 (판정 유보)",
            "hold_body": "고주사율 4K 144Hz+ DSC 압축 대역폭, 모니터 데이지체인, 구형 인텔 맥·리눅스 커널 조합은 모니터 입력 버전(DP 1.4 DSC 유무)과 케이블 규격에 따라 작동 여부가 달라집니다. 잘못된 구매를 막기 위해 아래 공식 사양을 먼저 대조하세요.",
            "hold_checks": [
                "Apple 공식 기술 사양(support.apple.com)에서 정확한 연식·칩셋의 외부 디스플레이 최대 대수 및 주사율 확인",
                "모니터가 DisplayPort MST 데이지체인 전용인지(macOS 미지원) Thunderbolt 데이지체인인지 구분",
                "리눅스 환경일 경우 DisplayLink 공식 드라이버(Ubuntu 외 배포판) 커널 호환 여부 사전 확인",
            ],
            "win_badge": "네이티브 MST · DisplayLink 모두 호환",
            "win_dual_head": "윈도우 USB4/TB4 노트북은 일반 MST 멀티 모니터 독을 드라이버 없이 바로 쓸 수 있습니다",
            "win_single_head": "단일 4K@60Hz 출력 + PD 충전 허브로 충분합니다",
            "win_body": "macOS와 달리 윈도우 11은 DisplayPort MST 분배를 기본 지원하므로 별도 소프트웨어 설치 없이 멀티 HDMI/DP 도킹스테이션을 사용할 수 있습니다.",
            "native_ok_badge": "네이티브 단일 모니터 완벽 호환",
            "single_head": "모든 M1~M4 맥북은 별도 드라이버 없이 단일 4K@60Hz 모니터를 기본 지원합니다",
            "single_body": "고가 DisplayLink 독을 살 필요가 없습니다. 휴대용이면 100W PD 패스스루 7-in-1 허브를, 데스크 고정형 고성능 확장이면 Thunderbolt 4 독을 선택하세요.",
            "hdcp_warn_badge": "주의 · DisplayLink 사용 시 OTT(HDCP) 검은 화면 제약",
            "m12_hdcp_head": "M1·M2 기본칩은 DisplayLink 독으로만 듀얼 확장이 되지만, 넷플릭스 등 HDCP 영상이 차단됩니다",
            "m12_hdcp_body": "Apple 하드웨어 제한상 M1/M2 기본칩은 덮개를 닫아도 네이티브 외부 모니터가 1대뿐입니다. 듀얼 구성을 하려면 DisplayLink 독이 필수이나, DisplayLink 활성화 중에는 브라우저 하드웨어 가속/HDCP 보안 때문에 OTT 화면이 검게 나옵니다. OTT 시청이 잦다면 '34~49인치 단일 울트라와이드 모니터 + 네이티브 허브' 구성을 권장합니다.",
            "dl_req_badge": "DisplayLink 전용 독 필수 (일반 허브 구매 주의)",
            "m12_dl_head": "M1·M2 기본칩 듀얼 모니터는 반드시 'DisplayLink 칩 탑재 독' + 전용 앱 설치가 필요합니다",
            "m12_dl_body": "일반 C타입 듀얼 HDMI 허브(MST 방식)나 정통 썬더볼트 독을 꽂아도 M1/M2 기본칩에서는 모니터 1대만 켜지거나 화면이 복제됩니다. DisplayLink 인증 독을 연결하고 macOS용 DisplayLink Manager 앱을 설치해야 2대 독립 확장이 작동합니다.",
            "native_clamshell_badge": "클램쉘 네이티브 듀얼 호환 (무드라이버 · HDCP 지원)",
            "m3_closed_head": "M3 에어 / M3 기본형 14인치 프로는 덮개를 닫으면 네이티브 듀얼 모니터가 바로 작동합니다!",
            "m3_closed_body": "전원 어댑터(PD 충전)를 연결하고 노트북 덮개를 닫으면 DisplayLink 드라이버 없이도 네이티브 듀얼 모니터와 넷플릭스 HDCP 재생이 모두 작동합니다. 단, 윈도우용 MST 허브는 여전히 화면이 복제되므로 정통 Thunderbolt 4 독과 수직 거치대 조합이 가장 안정적입니다.",
            "m3_open_hdcp_head": "덮개를 연 채 3화면(내장+외장2)을 쓰면 DisplayLink가 필요해 OTT 제약이 생깁니다",
            "m3_open_hdcp_body": "M3 기본칩에서 덮개를 닫고 클램쉘로 전환하면 정통 Thunderbolt 4 독으로 HDCP 제약 없는 네이티브 듀얼 구성이 가능합니다! 굳이 덮개를 열어 3화면을 써야 할 때만 DisplayLink 독을 선택하세요.",
            "m3_open_dl_head": "덮개를 열어둔 상태(내장+외장 2대)에서는 DisplayLink 독이 필요합니다",
            "m3_open_dl_body": "M3 기본칩은 덮개를 열면 네이티브 외장 출력이 1대로 제한됩니다. 내장 화면까지 총 3화면을 쓰려면 DisplayLink 독을, 드라이버 없이 깔끔한 듀얼을 원하면 덮개를 닫고 Thunderbolt 4 독을 선택하세요.",
            "native_dual_badge": "네이티브 듀얼 모니터 완벽 지원 (Thunderbolt 4 권장)",
            "promax_head": "선택하신 칩셋은 노트북 화면을 연 상태에서도 네이티브 듀얼 모니터와 HDCP를 기본 지원합니다",
            "promax_body": "DisplayLink 압축 독을 쓸 이유가 전혀 없습니다. 대역폭 손실과 CPU 점유가 없는 정통 Thunderbolt 4 도킹스테이션을 연결하세요.",
            "mst_warn_title": "⚠️ 절대 피해야 할 오구매 1순위: 윈도우 전용 MST 멀티 HDMI 허브",
            "mst_warn_desc": "상세페이지 작은 글씨에 'macOS는 확장 미지원(미러링만 지원, A+B+B)'이라고 적힌 일반 USB-C 멀티 HDMI 허브는 맥북 Pro/Max·M4에 꽂아도 두 모니터에 똑같은 화면만 나옵니다.",
            "rec_heading": "교차 검증된 호환 장비 확인 (실시간 조건 대조)",
            "btn_disc": BUTTON_DISCLOSURE_KO,
        }
        foot_note = "본 판별기는 Apple 공식 외부 디스플레이 지원 문서 및 Thunderbolt 4 / DisplayLink 기술 규격을 기준으로 작성되었습니다. 대한민국 수령 직구 시 중국·기타국발 미화 150달러, 미국발 목록통관 적격 200달러 면세 기준을 실제 결제창 금액으로 확인하세요."
    else:
        title = f"MacBook Dual-Monitor Dock Compatibility Checker (M1 / M2 / M3 / M4) | {cfg['site']['brand_name']}"
        desc = "Check whether your exact MacBook Air or MacBook Pro chip needs DisplayLink, Clamshell Thunderbolt 4, or avoids macOS MST mirroring traps before buying a dock."
        h1 = "MacBook Dual-Monitor Dock Compatibility Checker"
        lead = "Stop buying 'Dual 4K HDMI' USB-C hubs that only mirror screens on macOS. Select your exact MacBook chip, lid preference, and DRM streaming requirement below. Only setups cross-verified against official Apple external display specs and DisplayLink / Thunderbolt 4 rules are recommended; unverified edge cases are marked Hold."
        labels = ("1. Laptop Model & Chip", "2. External Monitors Needed", "3. Laptop Lid Mode", "4. Daily Netflix / Apple TV+ (HDCP DRM) Playback")
        chip_opts = [
            ("m1_m2_base", "MacBook Air M1 / M2 (13\" & 15\") or 13\" MacBook Pro (Base M1 / M2)"),
            ("m3_base", "MacBook Air M3 (13\" & 15\") or 14\" MacBook Pro (Base M3 w/ macOS 14.6+)"),
            ("m4_base", "MacBook Pro 14\" / Air (Base M4 chip)"),
            ("pro_max", "MacBook Pro 14\" & 16\" (M1 / M2 / M3 / M4 Pro or Max)"),
            ("windows_usb4", "Windows 11 Laptop (USB4 / Thunderbolt 4)"),
            ("other_unverified", "Older Intel Mac / Linux / Dual 4K@144Hz DSC or Daisy-Chain Monitor"),
        ]
        mon_opts = [("2", "2 Extended External Monitors (Dual Independent Screens)"), ("1", "1 External Monitor (Single 4K or Ultrawide)")]
        lid_opts = [("open", "Lid Open (Use MacBook screen + external displays)"), ("closed", "Clamshell Lid Closed (AC power attached)")]
        hdcp_opts = [("no", "Coding, Docs, Browsers & Productivity (can unplug for DRM video)"), ("yes", "Must play HDCP streaming (Netflix / Apple TV+) with dock active")]
        t_data = {
            "hold_badge": "Hold — Manual Spec Check Required",
            "hold_head": "Verdict Held: Do not buy blindly for this custom configuration",
            "hold_body": "High-refresh Dual 4K@144Hz DSC compression, DisplayPort daisy-chaining, older Intel Macs, and non-Ubuntu Linux kernels depend heavily on exact monitor DP 1.4 DSC firmware and OS drivers. Rather than guessing, verify these three points first:",
            "hold_checks": [
                "Look up your exact model identifier on support.apple.com to confirm native external display pipelines and DSC refresh limits.",
                "Confirm whether your monitor daisy-chains via DisplayPort MST (blocked for extended screens on macOS) vs true Thunderbolt.",
                "On Linux, verify official DisplayLink kernel module support for your exact kernel version before buying any USB graphics dock.",
            ],
            "win_badge": "Native MST & DisplayLink Supported",
            "win_dual_head": "Windows 11 USB4 / TB4 laptops run standard MST multi-HDMI docks driver-free",
            "win_single_head": "A single-4K@60Hz 100W PD hub covers this setup cleanly",
            "win_body": "Unlike macOS, Windows natively supports DisplayPort Multi-Stream Transport (MST), so multi-HDMI docks extend screens out of the box without software drivers.",
            "native_ok_badge": "Native Single-Monitor Match",
            "single_head": "Every M1–M4 MacBook drives one 4K@60Hz external display natively without DisplayLink",
            "single_body": "Skip software-compressed DisplayLink hubs for a single display. Pick a compact 100W PD USB-C hub for travel or a native Thunderbolt 4 dock for single-cable desk expansion.",
            "hdcp_warn_badge": "Warning — DisplayLink Blocks HDCP Video",
            "m12_hdcp_head": "Base M1/M2 Macs require DisplayLink for dual monitors, which blanks Netflix/Apple TV+ HDCP playback",
            "m12_hdcp_body": "Apple wired only 1 native external display pipeline into base M1 and M2 chips (even with the lid closed). A DisplayLink dock adds a second 4K@60Hz screen via software, but macOS disables HDCP DRM playback while DisplayLink screen capture is active. Consider one 34\"–49\" ultrawide on a native hub if you stream daily.",
            "dl_req_badge": "DisplayLink Dock Required",
            "m12_dl_head": "Base M1/M2 MacBooks require a DisplayLink-equipped dock + macOS DisplayLink Manager app",
            "m12_dl_body": "Standard USB-C dual-HDMI hubs (MST) and even flagship Thunderbolt 4 docks can only light up one external monitor natively on base M1/M2 Macs. Choose a verified DisplayLink dock for two independent 4K@60Hz desktops.",
            "native_clamshell_badge": "Native Clamshell Dual Match (Zero Drivers · Full HDCP)",
            "m3_closed_head": "Closing the lid on Base M3 unlocks 2 native external displays—no DisplayLink needed!",
            "m3_closed_body": "With AC/PD power connected and the lid closed in a vertical stand, M3 Air and base 14\" M3 Pro (macOS 14.6+) drive two native external monitors with full GPU acceleration and HDCP support. Avoid Windows MST splitters—use a true Thunderbolt 4 dock.",
            "m3_open_hdcp_head": "Keeping the lid open on Base M3 forces DisplayLink (and triggers HDCP streaming limits)",
            "m3_open_hdcp_body": "Tip: simply closing the MacBook lid lets Base M3 drive two external screens natively over Thunderbolt 4 with full Netflix/Apple TV+ support! Only choose DisplayLink if you strictly need 3 active screens (internal + 2 externals).",
            "m3_open_dl_head": "Lid-open 3-screen mode (internal + 2 externals) on Base M3 requires DisplayLink",
            "m3_open_dl_body": "Base M3 supports 1 external display with the lid open, or 2 native external displays with the lid closed. Pick DisplayLink for lid-open dual monitors, or pair a Thunderbolt 4 dock with a vertical stand for driver-free clamshell dual displays.",
            "native_dual_badge": "Native Dual-Display Match (Thunderbolt 4 Recommended)",
            "promax_head": "Your Mac chip drives 2+ external displays natively with the lid open and full HDCP",
            "promax_body": "Skip DisplayLink compression completely. Use a true Thunderbolt 4 dock for uncompressed 6K/4K@60Hz output, 98W charging, and 2.5GbE.",
            "mst_warn_title": "⚠️ #1 Return Trap on macOS: Windows MST Dual-HDMI Splitters",
            "mst_warn_desc": "Generic USB-C hubs with two HDMI ports rely on DisplayPort MST, which macOS does not support for extended desktops—even on M4 or M3 Max, both HDMI monitors will show the exact same mirrored image.",
            "rec_heading": "Cross-Verified Hardware Matches (Compare Live Store Options)",
            "btn_disc": BUTTON_DISCLOSURE_EN,
        }
        foot_note = "Cross-checked against Apple official external display specifications and Thunderbolt 4 / DisplayLink architecture. US buyers: check 'Ships from US' on Amazon vs cross-border import charges at checkout on AliExpress."

    def sel(name: str, opts: list[tuple[str, str]]) -> str:
        return f'<select name="{name}" class="tool-sel">' + "".join(
            f'<option value="{_esc(k)}">{_esc(v)}</option>' for k, v in opts
        ) + "</select>"

    payload = json.dumps({"t": t_data, "cards": cards}, ensure_ascii=False).replace("</", "<\\/")
    guide_link = (
        '<p style="margin-top:18px;font-size:14px"><a href="../../guides/macbook-m1-m2-m3-dual-monitor-dock-guide/">Read full technical breakdown: Why macOS Mirrors Dual-HDMI Hubs →</a></p>'
        if lang == "en"
        else '<p style="margin-top:18px;font-size:14px"><a href="../../c/hubs/">전체 독·허브 검수 목록 보기 →</a></p>'
    )

    body = f"""
<body class="{lang}">
  {legal_fn(lang)}
  {header_fn(lang, up, cfg, f"{up}{other}/tools/macbook-dock-checker/")}
  <main class="wrap" data-dock-tool data-lang="{lang}">
    <nav aria-label="{'이동 경로' if lang == 'ko' else 'Breadcrumb'}">
      <ol class="crumbs">
        <li><a href="../../">{'홈' if lang == 'ko' else 'Home'}</a></li>
        <li> / </li>
        <li aria-current="page">{_esc(h1)}</li>
      </ol>
    </nav>
    <section class="tool-hero">
      <span class="tag">{'호환성 판별 도구' if lang == 'ko' else 'Interactive Compatibility Tool'}</span>
      <h1>{_esc(h1)}</h1>
      <p class="dek">{_esc(lead)}</p>
    </section>

    <section class="panel tool-form" aria-label="Compatibility Inputs">
      <div class="tool-fields">
        <label><span>{_esc(labels[0])}</span>{sel('mac_chip', chip_opts)}</label>
        <label><span>{_esc(labels[1])}</span>{sel('monitors', mon_opts)}</label>
        <label><span>{_esc(labels[2])}</span>{sel('lid_mode', lid_opts)}</label>
        <label><span>{_esc(labels[3])}</span>{sel('hdcp_need', hdcp_opts)}</label>
      </div>
    </section>

    <section class="tool-out" data-dock-result aria-live="polite"></section>
    <p class="tool-foot-note">{_esc(foot_note)}</p>
    {guide_link}
    <script type="application/json" data-dock-json>{payload}</script>
  </main>
  {footer_fn(lang, up, cfg)}
  <script src="{up}assets/app.js" defer></script>
  <script>{DOCK_TOOL_JS}</script>
</body>
</html>
"""
    return head_fn(lang=lang, title=title, description=desc, up=up, cfg=cfg, path=path, alternates=alternates) + body


def render_en_guides_index(
    *,
    cfg: dict,
    head_fn: Callable[..., str],
    legal_fn: Callable[[str], str],
    header_fn: Callable[[str, str, dict, str], str],
    footer_fn: Callable[[str, str, dict], str],
) -> str:
    up = "../../"
    brand = cfg["site"]["brand_name"]
    title = f"Hardware Compatibility & Buying Guides (MacBook, GaN, Controllers, SSDs) | {brand}"
    desc = "12 non-template engineering buying guides covering Apple Silicon dual-monitor docks, USB4 thermals, TSA 100Wh power banks, Hall-effect/TMR controllers, and Budget Setup Picks."
    cards = []
    for g in GUIDES_EN:
        cards.append(
            f'<article class="panel guide-card">'
            f'<span class="tag">{_esc(g["pillar"])}</span>'
            f'<h2><a href="{_esc(g["slug"])}/">{_esc(g["title"])}</a></h2>'
            f'<p>{_esc(g["summary"])}</p>'
            f'<span class="gc-meta">Reviewed {_esc(g["reviewed_at"])} · {len(g["product_ids"])} vetted models compared →</span>'
            f'</article>'
        )

    body = f"""
<body class="en">
  {legal_fn("en")}
  {header_fn("en", up, cfg, f"{up}ko/tools/macbook-dock-checker/")}
  <main class="wrap">
    <nav aria-label="Breadcrumb"><ol class="crumbs"><li><a href="../">Home</a></li><li> / </li><li aria-current="page">Buying Guides</li></ol></nav>
    <header class="tool-hero">
      <span class="tag">Original Decision Guides · Zero Stale Prices</span>
      <h1>Hardware Compatibility &amp; Setup Buying Guides</h1>
      <p class="dek">Every guide below tests protocol compatibility, real-world caveats, and explicit exclusion rules ("who should skip") before linking to domestic US Amazon and direct-import options.</p>
      <p style="margin-top:14px"><a class="btn btn-amazon" style="display:inline-flex;width:auto" href="../tools/macbook-dock-checker/">Launch Interactive MacBook Dual-Monitor Dock Checker →</a></p>
    </header>
    <div class="guide-grid">{''.join(cards)}</div>
  </main>
  {footer_fn("en", up, cfg)}
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    return head_fn(lang="en", title=title, description=desc, up=up, cfg=cfg, path="/en/guides/", alternates=None) + body


def render_en_guide_detail(
    *,
    guide: dict,
    items_by_id: dict[str, dict],
    cfg: dict,
    head_fn: Callable[..., str],
    legal_fn: Callable[[str], str],
    header_fn: Callable[[str, str, dict, str], str],
    footer_fn: Callable[[str, str, dict], str],
    slug_fn: Callable[[str], str],
) -> str:
    up = "../../../"
    brand = cfg["site"]["brand_name"]
    path = f"/en/guides/{guide['slug']}/"
    title = f"{guide['title']} | {brand}"

    ths = "".join(f'<th scope="col">{_esc(h)}</th>' for h in guide["matrix_headers"])
    trs = "".join(
        "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>"
        for row in guide["matrix_rows"]
    )
    secs = "".join(
        f'<section class="section"><h2>{_esc(sh)}</h2><p class="guide-p">{_esc(sp)}</p></section>'
        for sh, sp in guide["sections"]
    )
    excl = "".join(f"<li>{_esc(x)}</li>" for x in guide["exclusions"])
    prod_cards = "".join(
        _render_tool_product_card(items_by_id[pid], "en", "../../p/", slug_fn)
        for pid in guide["product_ids"]
        if pid in items_by_id
    )
    tool_banner = (
        '<div class="panel" style="padding:16px 20px;margin-top:20px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px">'
        '<div><strong>Interactive MacBook Dual-Monitor Dock Checker</strong><p style="font-size:14px;color:var(--ink-2)">Select your exact M1/M2/M3/M4 chip and lid mode for an instant compatibility check.</p></div>'
        '<a class="btn btn-amazon" href="../../tools/macbook-dock-checker/">Open Checker →</a></div>'
        if guide.get("tool_cta")
        else ""
    )

    body = f"""
<body class="en">
  {legal_fn("en")}
  {header_fn("en", up, cfg, f"{up}ko/")}
  <main class="wrap">
    <nav aria-label="Breadcrumb">
      <ol class="crumbs">
        <li><a href="../../">Home</a></li><li> / </li>
        <li><a href="../">Buying Guides</a></li><li> / </li>
        <li aria-current="page">{_esc(guide['pillar'])}</li>
      </ol>
    </nav>
    <article class="guide-article">
      <header class="tool-hero">
        <span class="tag">{_esc(guide['pillar'])} · Reviewed {_esc(guide['reviewed_at'])}</span>
        <h1>{_esc(guide['title'])}</h1>
        <p class="dek">{_esc(guide['summary'])}</p>
      </header>
      {tool_banner}
      <p class="guide-p" style="margin-top:20px">{_esc(guide['intro'])}</p>

      <section class="section">
        <h2>Compatibility &amp; Selection Matrix</h2>
        <div class="panel" style="overflow-x:auto">
          <table class="spec-table guide-matrix">
            <thead><tr>{ths}</tr></thead>
            <tbody>{trs}</tbody>
          </table>
        </div>
      </section>

      {secs}

      <section class="section">
        <h2>Who Should Skip These Setups (Exclusion Checklist)</h2>
        <div class="panel cons" style="padding:18px 22px;border-left:4px solid #D97706">
          <ul class="guide-excl">{excl}</ul>
        </div>
      </section>

      <section class="section">
        <h2>Vetted Hardware Referenced in This Guide</h2>
        <p style="font-size:13.5px;color:var(--muted);margin-bottom:12px">{_esc(BUTTON_DISCLOSURE_EN)} US shoppers: check "Ships from US" on Amazon vs checkout import charges on cross-border AliExpress listings.</p>
        <div class="tool-grid">{prod_cards}</div>
      </section>
    </article>
  </main>
  {footer_fn("en", up, cfg)}
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    return head_fn(lang="en", title=title, description=guide["summary"], up=up, cfg=cfg, path=path, alternates=None) + body
