"""Interactive tools and buying guides.

- MacBook Dual-Monitor Dock Compatibility Checker (/ko|en/tools/macbook-dock-checker/)
- AliExpress Promo & Customs Calculator with the sale-window traffic light (/ko|en/tools/ali-promo-calculator/)
- 12 non-template hardware decision guides in English (GUIDES_EN) and Korean (GUIDES_KO)
"""

from __future__ import annotations

import html
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from src.affiliate import BUTTON_DISCLOSURE_EN, BUTTON_DISCLOSURE_KO
from src.guides_ko import GUIDES_KO


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

  let completionTracked = false;
  function evaluate(userChanged = false) {
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

    const cardList = picks.map(id => DATA.cards[id] || '').filter(Boolean);
    const cardsHtml = cardList.join('');
    const condHtml = `<dl class="v-cond"><dt>${DATA.t.cond_label}</dt>${[chipSel, monSel, lidSel, hdcpSel].map(el => {
      const dd = document.createElement('dd');
      dd.textContent = el.options[el.selectedIndex].text;
      return dd.outerHTML;
    }).join('')}</dl>`;
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
        ${condHtml}
      </div>
      ${cardsHtml ? `<div class="tool-picks"><h3>${DATA.t.rec_heading}</h3><div class="tool-grid" data-count="${cardList.length}">${cardsHtml}</div><p class="btn-disc">${DATA.t.btn_disc}</p></div>` : ''}
    `;

    // Re-apply dynamic channel tracking on newly injected store links
    if (window.__gchApplyAttribution) window.__gchApplyAttribution(out);
    if (userChanged && !completionTracked) {
      completionTracked = true;
      track('check_complete', { chip, mons, lid, hdcp, status });
    }
  }

  [chipSel, monSel, lidSel, hdcpSel].forEach(el => el.addEventListener('change', () => evaluate(true)));
  const logToolView = () => track('tool_view', { tool: 'macbook-dock-checker' });
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', logToolView, { once: true });
  } else {
    logToolView();
  }
  evaluate();
})();
"""


def render_dock_checker_page(
    *,
    lang: str,
    items_by_id: dict[str, dict],
    cfg: dict,
    head_fn: Callable[..., str],
    legal_fn: Callable[[str], str],
    header_fn: Callable[[str, str, dict, str], str],
    footer_fn: Callable[[str, str, dict], str],
    card_fn: Callable[..., str],
    icon_fn: Callable[..., str],
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
        pid: card_fn(items_by_id[pid], lang)
        for pid in needed_ids
        if pid in items_by_id
    }

    if lang == "ko":
        title = f"맥북 모델·칩별 듀얼모니터 독 호환 판별기 (M1·M2·M3·M4) | {cfg['site']['brand_name']}"
        desc = "내 맥북 에어·프로 칩셋과 클램쉘 여부, 넷플릭스(HDCP) 사용 여부에 맞춰 화면 복제(미러링) 실패 없는 도킹스테이션 구성을 즉시 판별합니다."
        h1 = "맥북 모델·칩별 듀얼모니터 독 호환 판별기"
        lead = "맥북에서 '듀얼 HDMI 허브'를 샀다가 두 모니터에 똑같은 화면만 복제되어 반품하는 사고를 막기 위한 공식 사양 교차 검증 도구입니다. Apple 외부 디스플레이 사양과 DisplayLink·Thunderbolt 4 작동 조건이 확인된 조합만 추천하며, 불확실한 특수 구성은 억지 추천 대신 '판정 유보'로 표시합니다."
        labels = ("노트북 모델 · 칩셋", "연결할 외부 모니터 수", "노트북 덮개(클램쉘) 상태", "OTT 스트리밍(넷플릭스·티빙 등 HDCP) 상시 재생")
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
            "mst_warn_title": "절대 피해야 할 오구매 1순위: 윈도우 전용 MST 멀티 HDMI 허브",
            "cond_label": "판정에 사용한 조건",
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
        labels = ("Laptop Model & Chip", "External Monitors Needed", "Laptop Lid Mode", "Daily Netflix / Apple TV+ (HDCP DRM) Playback")
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
            "mst_warn_title": "#1 Return Trap on macOS: Windows MST Dual-HDMI Splitters",
            "cond_label": "Checked against",
            "mst_warn_desc": "Generic USB-C hubs with two HDMI ports rely on DisplayPort MST, which macOS does not support for extended desktops—even on M4 or M3 Max, both HDMI monitors will show the exact same mirrored image.",
            "rec_heading": "Cross-Verified Hardware Matches (Compare Live Store Options)",
            "btn_disc": BUTTON_DISCLOSURE_EN,
        }
        foot_note = "Cross-checked against Apple official external display specifications and Thunderbolt 4 / DisplayLink architecture. US buyers: check 'Ships from US' on Amazon vs cross-border import charges at checkout on AliExpress."

    def field(n: int, name: str, label: str, opts: list[tuple[str, str]]) -> str:
        options = "".join(f'<option value="{_esc(k)}">{_esc(v)}</option>' for k, v in opts)
        return (
            f'<li class="field"><label for="f-{name}"><span class="step">{n}</span><span>{_esc(label)}</span></label>'
            f'<span class="sel"><select id="f-{name}" name="{name}" class="tool-sel">{options}</select>{icon_fn("down", 16)}</span></li>'
        )

    payload = json.dumps({"t": t_data, "cards": cards}, ensure_ascii=False).replace("</", "<\\/")
    arrow = icon_fn("arrow", 14)
    guide_link = (
        f'<p class="tool-more"><a class="text-link" href="../../guides/macbook-m1-m2-m3-dual-monitor-dock-guide/">Read full technical breakdown: Why macOS Mirrors Dual-HDMI Hubs {arrow}</a></p>'
        if lang == "en"
        else f'<p class="tool-more"><a class="text-link" href="../../guides/macbook-m1-m2-m3-dual-monitor-dock-guide/">칩별 독 선택 가이드 전문 읽기: 맥북 듀얼모니터가 복제 화면만 나오는 이유 {arrow}</a></p>'
    )
    form_lbl = "호환 조건 입력" if lang == "ko" else "Compatibility inputs"

    body = f"""
<body class="{lang}">
  {legal_fn(lang)}
  {header_fn(lang, up, cfg, f"{up}{other}/tools/macbook-dock-checker/")}
  <main class="wrap" data-dock-tool data-lang="{lang}">
    <nav aria-label="{'이동 경로' if lang == 'ko' else 'Breadcrumb'}">
      <ol class="crumbs">
        <li><a href="../../">{'홈' if lang == 'ko' else 'Home'}</a></li>
        <li> / </li>
        <li aria-current="page">{'호환성 판별 도구' if lang == 'ko' else 'Interactive Compatibility Tool'}</li>
      </ol>
    </nav>
    <header class="page-head tool-hero">
      <h1>{_esc(h1)}</h1>
      <p class="dek">{_esc(lead)}</p>
    </header>

    <section class="sheet tool-form" aria-label="{form_lbl}">
      <ol class="tool-fields">
        {field(1, 'mac_chip', labels[0], chip_opts)}
        {field(2, 'monitors', labels[1], mon_opts)}
        {field(3, 'lid_mode', labels[2], lid_opts)}
        {field(4, 'hdcp_need', labels[3], hdcp_opts)}
      </ol>
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




# --------------------------------------------------------------------------------------
# Buying guides index + detail. KO and EN share one renderer; hreflang pairs link the two.
# --------------------------------------------------------------------------------------

GUIDES_BY_LANG: dict[str, list[dict]] = {"en": GUIDES_EN, "ko": GUIDES_KO}

_GUIDE_T = {
    "en": {
        "home": "Home",
        "guides": "Buying Guides",
        "index_title": "Hardware Compatibility & Buying Guides (MacBook, GaN, Controllers, SSDs) | {brand}",
        "index_desc": "12 non-template engineering buying guides covering Apple Silicon dual-monitor docks, USB4 thermals, TSA 100Wh power banks, Hall-effect/TMR controllers, and Budget Setup Picks.",
        "index_h1": "Hardware Compatibility & Setup Buying Guides",
        "index_dek": 'Every guide below tests protocol compatibility, real-world caveats, and explicit exclusion rules ("who should skip") before linking to domestic US Amazon and direct-import options.',
        "index_meta": "Original Decision Guides · Zero Stale Prices",
        "index_cta_dock": "Launch Interactive MacBook Dual-Monitor Dock Checker",
        "index_cta_promo": "AliExpress Promo & Customs Calculator",
        "card_meta": "Reviewed {date} · {n} vetted models compared",
        "meta": "{pillar} · Reviewed {date}",
        "matrix_h": "Compatibility & Selection Matrix",
        "matrix_aria": "Compatibility and selection matrix",
        "excl_h": "Who Should Skip These Setups (Exclusion Checklist)",
        "prods_h": "Vetted Hardware Referenced in This Guide",
        "disc": BUTTON_DISCLOSURE_EN + ' US shoppers: check "Ships from US" on Amazon vs checkout import charges on cross-border AliExpress listings.',
        "dock_strong": "Interactive MacBook Dual-Monitor Dock Checker",
        "dock_p": "Select your exact M1/M2/M3/M4 chip and lid mode for an instant compatibility check.",
        "dock_btn": "Open Checker",
        "promo_strong": "AliExpress Promo & Customs Calculator",
        "promo_p": "Stack a store coupon, coins and the promo-code tier on any vetted model, then compare the result with the manufacturer reference MSRP.",
        "promo_btn": "Open Calculator",
        "tool_aria": "Interactive tools",
        "crumb_aria": "Breadcrumb",
    },
    "ko": {
        "home": "홈",
        "guides": "구매 가이드",
        "index_title": "PC·데스크 기어 구매 가이드 12선 (맥북 독·GaN 충전·보조배터리·외장SSD) | {brand}",
        "index_desc": "KC 인증, 220V 플러그, $150·$200 통관 기준, 쿠팡 로켓 vs 알리 초이스데이까지 한국 구매자 기준으로 정리한 하드웨어 구매 가이드 12편.",
        "index_h1": "한국 구매자를 위한 하드웨어 호환성·구매 가이드",
        "index_dek": "모든 가이드는 규격 호환성과 실사용 단점, 그리고 '이런 분은 사지 마세요' 제외 기준을 먼저 정리한 뒤 쿠팡 국내 배송과 알리 직구 경로를 비교합니다.",
        "index_meta": "직접 작성한 결정 가이드 · 정적 가격 미보관",
        "index_cta_dock": "맥북 듀얼모니터 독 호환 판별기 열기",
        "index_cta_promo": "알리 코드·통관 계산기",
        "card_meta": "검수일 {date} · 검수 모델 {n}종 비교",
        "meta": "{pillar} · 검수일 {date}",
        "matrix_h": "선택 기준 매트릭스",
        "matrix_aria": "선택 기준 매트릭스",
        "kr_h": "한국 구매자 체크: KC·220V·통관·구매 경로",
        "excl_h": "이런 분은 사지 마세요",
        "prods_h": "이 가이드에서 다룬 검수 완료 기어",
        "disc": BUTTON_DISCLOSURE_KO + " 대한민국 수령 시 중국·기타국발 $150, 미국발 목록통관 $200 면세 기준을 결제창 금액으로 확인하세요.",
        "dock_strong": "맥북 모델·칩별 듀얼모니터 독 호환 판별기",
        "dock_p": "칩셋, 덮개 상태, OTT 사용 여부를 고르면 맞는 독 구성을 바로 보여 줍니다.",
        "dock_btn": "판별기 열기",
        "promo_strong": "알리 코드 체감가·통관 계산기",
        "promo_p": "스토어 쿠폰·코인·프로모 코드 구간을 적용한 예상 결제가와 $150·$200 면세선 여유를 바로 계산합니다.",
        "promo_btn": "계산기 열기",
        "tool_aria": "판별·계산 도구",
        "crumb_aria": "이동 경로",
    },
}


def _tool_strip(kind: str, lang: str, href: str, icon_fn: Callable[..., str]) -> str:
    """Featured-tool strip linking to the dock checker or the promo calculator."""
    g = _GUIDE_T[lang]
    icon = "dual" if kind == "dock" else "calc"
    return (
        f'<section class="feat-strip" aria-label="{g["tool_aria"]}"><span class="feat-ic">{icon_fn(icon, 22)}</span>'
        f'<div><strong>{_esc(g[kind + "_strong"])}</strong><p>{_esc(g[kind + "_p"])}</p></div>'
        f'<div class="feat-actions"><a class="btn btn-primary btn-s" href="{href}">{_esc(g[kind + "_btn"])} {icon_fn("arrow", 14)}</a></div>'
        f'</section>'
    )


def render_guides_index(
    *,
    lang: str,
    cfg: dict,
    head_fn: Callable[..., str],
    legal_fn: Callable[[str], str],
    header_fn: Callable[[str, str, dict, str], str],
    footer_fn: Callable[[str, str, dict], str],
    items_by_id: dict[str, dict],
    plate_fn: Callable[..., str],
    icon_fn: Callable[..., str],
) -> str:
    up = "../../"
    g = _GUIDE_T[lang]
    other = "en" if lang == "ko" else "ko"
    guides = GUIDES_BY_LANG[lang]
    title = g["index_title"].format(brand=cfg["site"]["brand_name"])

    def card(guide: dict) -> str:
        plates = "".join(plate_fn(items_by_id[pid], up) for pid in guide["product_ids"][:4] if pid in items_by_id)
        meta = g["card_meta"].format(date=guide["reviewed_at"], n=len(guide["product_ids"]))
        return (
            f'<article class="sheet guide-card">'
            f'<h3><a href="{_esc(guide["slug"])}/">{_esc(guide["title"])}</a></h3>'
            f'<p>{_esc(guide["summary"])}</p>'
            f'<div class="gc-foot"><span class="gc-plates" aria-hidden="true">{plates}</span>'
            f'<span class="gc-meta">{_esc(meta)}</span></div>'
            f'</article>'
        )

    pillars: dict[str, list[dict]] = {}
    for guide in guides:
        pillars.setdefault(guide["pillar"], []).append(guide)
    groups = "".join(
        f'<section class="guide-group"><h2>{_esc(pillar)}</h2>'
        f'<div class="guide-grid">{"".join(card(x) for x in gs)}</div></section>'
        for pillar, gs in pillars.items()
    )
    arrow = icon_fn("arrow", 15)

    body = f"""
<body class="{lang}">
  {legal_fn(lang)}
  {header_fn(lang, up, cfg, f"{up}{other}/guides/")}
  <main class="wrap">
    <nav aria-label="{g['crumb_aria']}"><ol class="crumbs"><li><a href="../">{g['home']}</a></li><li> / </li><li aria-current="page">{g['guides']}</li></ol></nav>
    <header class="page-head">
      <h1>{_esc(g['index_h1'])}</h1>
      <p class="dek">{_esc(g['index_dek'])}</p>
      <p class="page-meta">{_esc(g['index_meta'])}</p>
      <p class="page-act btn-row"><a class="btn btn-primary" href="../tools/macbook-dock-checker/">{_esc(g['index_cta_dock'])} {arrow}</a><a class="btn" href="../tools/ali-promo-calculator/">{_esc(g['index_cta_promo'])} {arrow}</a></p>
    </header>
    {groups}
  </main>
  {footer_fn(lang, up, cfg)}
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    return head_fn(lang=lang, title=title, description=g["index_desc"], up=up, cfg=cfg, path=f"/{lang}/guides/",
                   alternates={"ko": "/ko/guides/", "en": "/en/guides/"}) + body


def render_guide_detail(
    *,
    lang: str,
    guide: dict,
    items_by_id: dict[str, dict],
    cfg: dict,
    head_fn: Callable[..., str],
    legal_fn: Callable[[str], str],
    header_fn: Callable[[str, str, dict, str], str],
    footer_fn: Callable[[str, str, dict], str],
    card_fn: Callable[..., str],
    icon_fn: Callable[..., str],
) -> str:
    up = "../../../"
    g = _GUIDE_T[lang]
    other = "en" if lang == "ko" else "ko"
    slug = guide["slug"]
    path = f"/{lang}/guides/{slug}/"
    title = f"{guide['title']} | {cfg['site']['brand_name']}"

    ths = "".join(f'<th scope="col">{_esc(h)}</th>' for h in guide["matrix_headers"])
    trs = "".join(
        "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>"
        for row in guide["matrix_rows"]
    )
    secs = "".join(
        f'<section class="section"><h2>{_esc(sh)}</h2><p class="guide-p">{_esc(sp)}</p></section>'
        for sh, sp in guide["sections"]
    )
    kr_check = ""
    if guide.get("kr_check"):
        rows = "".join(f'<tr><th scope="row">{_esc(k)}</th><td>{_esc(v)}</td></tr>' for k, v in guide["kr_check"])
        kr_check = (
            f'<section class="section"><h2>{_esc(g["kr_h"])}</h2>'
            f'<div class="table-sheet"><table class="spec-table kr-check"><tbody>{rows}</tbody></table></div></section>'
        )
    excl = "".join(f"<li>{_esc(x)}</li>" for x in guide["exclusions"])
    prods = [items_by_id[pid] for pid in guide["product_ids"] if pid in items_by_id]
    prod_cards = "".join(card_fn(it, lang, hl="h3") for it in prods)

    wants_dock = guide.get("tool") == "dock" or bool(guide.get("tool_cta"))
    top_tool = _tool_strip("dock", lang, "../../tools/macbook-dock-checker/", icon_fn) if wants_dock else ""
    promo_tool = _tool_strip("promo", lang, "../../tools/ali-promo-calculator/", icon_fn)

    body = f"""
<body class="{lang}">
  {legal_fn(lang)}
  {header_fn(lang, up, cfg, f"{up}{other}/guides/{slug}/")}
  <main class="wrap">
    <nav aria-label="{g['crumb_aria']}">
      <ol class="crumbs">
        <li><a href="../../">{g['home']}</a></li><li> / </li>
        <li><a href="../">{g['guides']}</a></li><li> / </li>
        <li aria-current="page">{_esc(guide['pillar'])}</li>
      </ol>
    </nav>
    <article class="guide-article">
      <header class="page-head">
        <h1>{_esc(guide['title'])}</h1>
        <p class="dek">{_esc(guide['summary'])}</p>
        <p class="page-meta">{_esc(g['meta'].format(pillar=guide['pillar'], date=guide['reviewed_at']))}</p>
      </header>
      {top_tool}
      <p class="guide-p lead">{_esc(guide['intro'])}</p>

      <section class="section">
        <h2>{_esc(g['matrix_h'])}</h2>
        <div class="table-sheet table-scroll" tabindex="0" role="region" aria-label="{g['matrix_aria']}">
          <table class="spec-table guide-matrix">
            <thead><tr>{ths}</tr></thead>
            <tbody>{trs}</tbody>
          </table>
        </div>
      </section>

      {secs}
      {kr_check}

      <section class="section">
        <h2>{_esc(g['excl_h'])}</h2>
        <div class="notice excl">
          <ul class="guide-excl">{excl}</ul>
        </div>
      </section>

      <section class="section">
        <h2>{_esc(g['prods_h'])}</h2>
        <div class="tool-grid" data-count="{len(prods)}">{prod_cards}</div>
        <p class="btn-disc">{_esc(g['disc'])}</p>
      </section>
      {promo_tool}
    </article>
  </main>
  {footer_fn(lang, up, cfg)}
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    return head_fn(lang=lang, title=title, description=guide["summary"], up=up, cfg=cfg, path=path,
                   alternates={"ko": f"/ko/guides/{slug}/", "en": f"/en/guides/{slug}/"}) + body


def render_en_guides_index(**kwargs) -> str:
    """Backward-compatible English wrapper."""
    return render_guides_index(lang="en", **kwargs)


def render_en_guide_detail(**kwargs) -> str:
    """Backward-compatible English wrapper."""
    return render_guide_detail(lang="en", **kwargs)


# --------------------------------------------------------------------------------------
# AliExpress promo tiers, sale-window traffic light and the Promo & Customs Calculator
# --------------------------------------------------------------------------------------

PROMO_TIERS_FILE = "ali_promo_tiers.json"
DEFAULT_KRW_PER_USD = 1400
# Reference clock per language: Korea Standard Time for /ko/, US Pacific (standard) for /en/.
SALE_TZ_HOURS = {"ko": 9, "en": -8}
KR_DUTY_FREE_USD = {"cn": 150.0, "us": 200.0}

_FALLBACK_PROMO = {
    "notice": {
        "ko": "선착순 소진·일부 품목 제외 가능 — 결제창 최종 적용 확인",
        "en": "Limited redemptions & exclusions apply — verify at checkout",
    },
    "reference_tiers": {
        "label": {"ko": "초이스데이·월간 프로모 참고 구간", "en": "Choice Day / monthly promo reference tiers"},
        "tiers": [
            {"min_spend_usd": 19, "off_usd": 2, "code": None},
            {"min_spend_usd": 39, "off_usd": 5, "code": None},
            {"min_spend_usd": 79, "off_usd": 10, "code": None},
            {"min_spend_usd": 159, "off_usd": 20, "code": None},
            {"min_spend_usd": 299, "off_usd": 40, "code": None},
        ],
    },
    "events": [],
}

SALE_COPY = {
    "ko": {
        "mega": ("go", "매수 적기 · 연말 메가세일·블프 구간",
                 "11월 11~18일, 11월 20일~12월 3일 구간입니다. 코드 구간과 쿠팡·카드 할인을 실결제가로 대조하세요."),
        "choice": ("go", "매수 적기 · 알리 초이스데이 주간",
                   "매월 1~7일 구간입니다. 초이스 상품의 코드 구간을 결제창에서 확인하세요."),
        "hold": ("hold", "대기 권장 · 매월 1일 초이스데이 임박 (급하면 쿠팡·아마존)",
                 "매월 26일~말일 구간입니다. 급하지 않은 직구는 1일 이후로 미루는 편이 유리합니다."),
        "standard": ("std", "상시 코드·카드할인 구간 (쿠팡·아마존 실결제가 대조 필수)",
                     "큰 행사가 없는 구간입니다. 상시 코드와 카드 즉시할인을 쿠팡·아마존 실결제가와 비교하세요."),
    },
    "en": {
        "mega": ("go", "BUY WINDOW · Mega Sale Window",
                 "Nov 11-18 and Nov 20 - Dec 3. Stack the code tier, then compare against Amazon Prime checkout totals."),
        "choice": ("go", "BUY WINDOW · Choice Day Week",
                   "Days 1-7 of each month. Check the Choice code tier at checkout."),
        "hold": ("hold", "HOLD · Choice Day Opens 1st (Use Prime if Urgent)",
                 "Days 26-31. Non-urgent direct imports usually do better after the 1st."),
        "standard": ("std", "STANDARD WINDOW · Compare Prime vs Promo Code",
                     "No major event running. Compare everyday codes and card offers with Amazon Prime totals."),
    },
}


def load_promo_tiers(project_root: Path | None = None) -> dict:
    """Read data/ali_promo_tiers.json; fall back to the built-in reference ladder if it is missing or broken."""
    root = project_root or Path(__file__).resolve().parent.parent
    path = Path(root) / "data" / PROMO_TIERS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(_FALLBACK_PROMO))
    if not isinstance(data, dict) or not (data.get("reference_tiers") or {}).get("tiers"):
        return json.loads(json.dumps(_FALLBACK_PROMO))
    data.setdefault("notice", _FALLBACK_PROMO["notice"])
    data.setdefault("events", [])
    return data


def sale_reference_date(lang: str, now: datetime | None = None) -> date:
    """Calendar date on the language's reference clock (KST for ko, Pacific standard time for en)."""
    now = now or datetime.now(timezone.utc)
    return (now.astimezone(timezone.utc) + timedelta(hours=SALE_TZ_HOURS.get(lang, 0))).date()


def sale_window(day: date) -> str:
    """Sale traffic-light window for a calendar date: 'mega' | 'choice' | 'hold' | 'standard'."""
    if (day.month == 11 and (11 <= day.day <= 18 or day.day >= 20)) or (day.month == 12 and day.day <= 3):
        return "mega"
    if day.day <= 7:
        return "choice"
    if day.day >= 26:
        return "hold"
    return "standard"


def sale_signal(lang: str, day: date) -> dict:
    """Traffic-light state for a language and date: tone ('go' | 'hold' | 'std'), label and helper line."""
    window = sale_window(day)
    tone, label, sub = SALE_COPY[lang][window]
    return {"window": window, "tone": tone, "label": label, "sub": sub}


def _clean_tiers(tiers: list[dict]) -> list[dict]:
    out = []
    for t in tiers or []:
        try:
            spend, off = float(t["min_spend_usd"]), float(t["off_usd"])
        except (KeyError, TypeError, ValueError):
            continue
        if spend > 0 and 0 < off < spend:
            code = (t.get("code") or "").strip() or None
            out.append({"min_spend_usd": spend, "off_usd": off, "code": code})
    return sorted(out, key=lambda t: t["min_spend_usd"])


def promo_events_for_lang(data: dict, lang: str) -> list[dict]:
    """Dated promo events (with codes) that apply to a language edition, normalised for the page payload."""
    events = []
    for ev in data.get("events") or []:
        if lang not in (ev.get("langs") or []):
            continue
        tiers = _clean_tiers(ev.get("tiers") or [])
        if not (tiers and ev.get("starts") and ev.get("ends")):
            continue
        events.append({
            "id": ev.get("id", ""),
            "label": (ev.get("label") or {}).get(lang, ""),
            "source": (ev.get("source") or {}).get(lang, ""),
            "starts": ev["starts"],
            "ends": ev["ends"],
            "tiers": tiers,
        })
    return events


def active_promo(data: dict, lang: str, day: date) -> dict:
    """The promo ladder to show today: a dated event with codes when one is running, else the reference tiers."""
    iso = day.isoformat()
    for ev in promo_events_for_lang(data, lang):
        if ev["starts"] <= iso <= ev["ends"]:
            return {**ev, "kind": "event"}
    ref = data.get("reference_tiers") or {}
    return {
        "id": "reference",
        "kind": "reference",
        "label": (ref.get("label") or {}).get(lang, ""),
        "source": (ref.get("note") or {}).get(lang, ""),
        "tiers": _clean_tiers(ref.get("tiers") or []),
    }


def best_promo_tier(subtotal_usd: float, tiers: list[dict]) -> dict | None:
    """Highest-value tier whose minimum spend the post-coupon subtotal already meets."""
    eligible = [t for t in tiers if subtotal_usd >= t["min_spend_usd"]]
    return max(eligible, key=lambda t: (t["off_usd"], t["min_spend_usd"])) if eligible else None


def compute_promo_checkout(
    list_price_usd: float,
    *,
    store_coupon_usd: float = 0.0,
    coin_pct: float = 0.0,
    tiers: list[dict] | None = None,
    tier_choice: str | float = "auto",
    custom_off_usd: float = 0.0,
    krw_per_usd: float = DEFAULT_KRW_PER_USD,
    origin: str = "cn",
    msrp_usd: float | None = None,
) -> dict:
    """Reference implementation of the calculator maths (the page script mirrors it line for line).

    Order: coin discount on the list price -> seller store coupon -> promo-code tier judged on the
    post-coupon subtotal. Korea customs light: origin 'cn' uses the USD 150 line, 'us' the USD 200
    list-clearance line; origins 'domestic' / 'cross' (EN edition) carry no dollar threshold.
    """
    price = max(0.0, float(list_price_usd or 0))
    coin_pct = min(max(float(coin_pct or 0), 0.0), 100.0)
    coin_off = _r2(price * coin_pct / 100)
    after_coin = price - coin_off
    coupon_off = _r2(min(max(float(store_coupon_usd or 0), 0.0), after_coin))
    subtotal = _r2(after_coin - coupon_off)

    tiers = _clean_tiers(tiers or [])
    tier, tier_off, shortfall = None, 0.0, 0.0
    if tier_choice == "auto":
        tier = best_promo_tier(subtotal, tiers)
        tier_off = tier["off_usd"] if tier else 0.0
    elif tier_choice == "custom":
        tier_off = _r2(min(max(float(custom_off_usd or 0), 0.0), subtotal))
    elif tier_choice != "none":
        picked = next((t for t in tiers if t["min_spend_usd"] == float(tier_choice)), None)
        if picked and subtotal >= picked["min_spend_usd"]:
            tier, tier_off = picked, picked["off_usd"]
        elif picked:
            shortfall = _r2(picked["min_spend_usd"] - subtotal)

    net = _r2(max(0.0, subtotal - tier_off))
    upcoming = next((t for t in tiers if t["min_spend_usd"] > subtotal), None)
    result = {
        "list_price_usd": _r2(price),
        "coin_off_usd": coin_off,
        "coupon_off_usd": coupon_off,
        "subtotal_usd": subtotal,
        "tier": tier,
        "tier_off_usd": _r2(tier_off),
        "tier_shortfall_usd": shortfall,
        "next_tier": upcoming,
        "next_tier_gap_usd": _r2(upcoming["min_spend_usd"] - subtotal) if upcoming else 0.0,
        "net_usd": net,
        "net_krw": int(math.floor(net * float(krw_per_usd or 0) + 0.5)),
        "origin": origin,
    }
    if origin in KR_DUTY_FREE_USD:
        threshold = KR_DUTY_FREE_USD[origin]
        duty_free = net <= threshold
        result.update({
            "customs_threshold_usd": threshold,
            "duty_free": duty_free,
            "customs_margin_usd": _r2(threshold - net),
            "est_vat_usd": 0.0 if duty_free else _r2(net * 0.10),
        })
    else:
        result.update({"customs_threshold_usd": None, "duty_free": origin == "domestic",
                       "customs_margin_usd": None, "est_vat_usd": 0.0})
    if msrp_usd and msrp_usd > 0:
        result["vs_msrp_usd"] = _r2(float(msrp_usd) - net)
        result["vs_msrp_pct"] = round((float(msrp_usd) - net) / float(msrp_usd) * 100, 1)
    return result


def _r2(value: float) -> float:
    """Half-up rounding to cents; the page script uses the identical expression."""
    return math.floor(value * 100 + 0.5 + 1e-9) / 100


def kr_customs_anchor(msrp_usd: float) -> tuple[str, str]:
    """Customs-line verdict for the reference anchor strip, judged on the manufacturer reference MSRP."""
    if msrp_usd <= KR_DUTY_FREE_USD["cn"]:
        return "is-in", "$150 면세선 이내"
    if msrp_usd <= KR_DUTY_FREE_USD["us"]:
        return "is-edge", "$150 초과 · 미국발 $200 이내"
    return "is-over", "면세선 초과 · 부가세 10% 대상"


PROMO_TOOL_JS = r"""
(() => {
  const root = document.querySelector('[data-promo-tool]');
  if (!root) return;
  const D = JSON.parse(root.querySelector('[data-promo-json]').textContent);
  const T = D.t;
  const $ = s => root.querySelector(s);
  const f = {
    preset: $('[name="preset"]'), price: $('[name="price"]'), coupon: $('[name="coupon"]'),
    coin: $('[name="coin"]'), tier: $('[name="tier"]'), custom: $('[name="custom"]'),
    rate: $('[name="rate"]'), origin: $('[name="origin"]'),
  };
  const customWrap = $('[data-custom-wrap]');
  const tierSrc = $('[data-tier-source]');
  const out = $('[data-promo-result]');
  const byId = Object.fromEntries(D.products.map(p => [p.id, p]));

  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (tpl, v) => tpl.replace(/\{(\w+)\}/g, (_, k) => v[k]);
  const r2 = v => Math.floor(v * 100 + 0.5 + 1e-9) / 100;
  const usd = v => '$' + r2(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const whole = v => '$' + (Number.isInteger(v) ? v : r2(v));
  const num = (el, max) => {
    const v = el ? parseFloat(el.value) : NaN;
    return Number.isFinite(v) && v > 0 ? Math.min(v, max) : 0;
  };
  function track(evName, detail) {
    try { window.dispatchEvent(new CustomEvent('gch:funnel', { detail: Object.assign({ event: evName, lang: D.lang }, detail || {}) })); } catch (e) {}
  }

  // Which promo ladder is live today on the edition's reference clock (falls back to reference tiers).
  const today = new Date(Date.now() + D.tz * 3600000).toISOString().slice(0, 10);
  const promo = D.events.find(e => e.starts <= today && today <= e.ends) || D.ref;
  const TIERS = promo.tiers;
  if (tierSrc) tierSrc.textContent = [promo.label, promo.source].filter(Boolean).join(' · ');

  const tierLabel = t => fmt(T.tier_opt, { m: whole(t.min_spend_usd), o: whole(t.off_usd) }) + (t.code ? ' · ' + t.code : '');
  f.tier.innerHTML = [
    `<option value="auto">${esc(T.tier_auto)}</option>`,
    ...TIERS.map(t => `<option value="${t.min_spend_usd}">${esc(tierLabel(t))}</option>`),
    `<option value="custom">${esc(T.tier_custom)}</option>`,
    `<option value="none">${esc(T.tier_none)}</option>`,
  ].join('');

  function compute() {
    const price = num(f.price, 99999);
    const coinPct = num(f.coin, 100);
    const coinOff = r2(price * coinPct / 100);
    const afterCoin = price - coinOff;
    const couponOff = r2(Math.min(num(f.coupon, 99999), afterCoin));
    const subtotal = r2(afterCoin - couponOff);
    const choice = f.tier.value;
    let tier = null, tierOff = 0, shortfall = 0, picked = null;
    if (choice === 'auto') {
      TIERS.forEach(t => { if (subtotal >= t.min_spend_usd && (!tier || t.off_usd >= tier.off_usd)) tier = t; });
      tierOff = tier ? tier.off_usd : 0;
    } else if (choice === 'custom') {
      tierOff = r2(Math.min(num(f.custom, 99999), subtotal));
    } else if (choice !== 'none') {
      picked = TIERS.find(t => String(t.min_spend_usd) === choice) || null;
      if (picked && subtotal >= picked.min_spend_usd) { tier = picked; tierOff = picked.off_usd; }
      else if (picked) shortfall = r2(picked.min_spend_usd - subtotal);
    }
    const net = r2(Math.max(0, subtotal - tierOff));
    const next = TIERS.find(t => t.min_spend_usd > subtotal) || null;
    return { price, coinPct, coinOff, couponOff, subtotal, choice, tier, tierOff, shortfall, picked, net, next };
  }

  function customsBox(c) {
    const origin = f.origin.value;
    if (!c.price) {
      return `<div class="verdict-box is-hold customs-light"><span class="v-badge">${esc(T.empty_badge)}</span><h2>${esc(T.empty_head)}</h2></div>`;
    }
    if (origin === 'cn' || origin === 'us') {
      const line = origin === 'cn' ? 150 : 200;
      const gap = r2(Math.abs(line - c.net));
      if (c.net <= line) {
        return `<div class="verdict-box is-ok customs-light" data-customs="ok"><span class="v-badge">${esc(fmt(T.ok_badge, { g: usd(gap) }))}</span>` +
          `<h2>${esc(fmt(T.ok_head, { t: whole(line) }))}</h2><p>${esc(origin === 'cn' ? T.ok_body_cn : T.ok_body_us)}</p></div>`;
      }
      return `<div class="verdict-box is-warn customs-light" data-customs="over"><span class="v-badge">${esc(fmt(T.warn_badge, { t: whole(line), g: usd(gap) }))}</span>` +
        `<h2>${esc(fmt(T.warn_head, { v: usd(c.net * 0.1) }))}</h2><p>${esc(fmt(T.warn_body, { t: whole(line), g: usd(gap) }))}</p></div>`;
    }
    if (origin === 'domestic') {
      return `<div class="verdict-box is-ok customs-light" data-customs="ok"><span class="v-badge">${esc(T.dom_badge)}</span><h2>${esc(T.dom_head)}</h2><p>${esc(T.dom_body)}</p></div>`;
    }
    return `<div class="verdict-box is-warn customs-light" data-customs="over"><span class="v-badge">${esc(T.cross_badge)}</span><h2>${esc(T.cross_head)}</h2><p>${esc(T.cross_body)}</p></div>`;
  }

  function render() {
    customWrap.hidden = f.tier.value !== 'custom';
    const c = compute();
    const p = byId[f.preset.value] || null;
    const rate = f.rate ? num(f.rate, 99999) : 0;

    const lines = [`<div><dt>${esc(T.l_price)}</dt><dd>${usd(c.price)}</dd></div>`];
    if (c.coinOff) lines.push(`<div class="is-off"><dt>${esc(fmt(T.l_coin, { p: c.coinPct }))}</dt><dd>−${usd(c.coinOff)}</dd></div>`);
    if (c.couponOff) lines.push(`<div class="is-off"><dt>${esc(T.l_coupon)}</dt><dd>−${usd(c.couponOff)}</dd></div>`);
    if (c.tierOff) {
      const lbl = c.tier ? fmt(T.l_tier, { m: whole(c.tier.min_spend_usd) }) : T.l_custom;
      lines.push(`<div class="is-off"><dt>${esc(lbl)}</dt><dd>−${usd(c.tierOff)}</dd></div>`);
    }

    let code = '';
    if (c.tier && c.tier.code) {
      code = `<span>${esc(T.code_lbl)}</span><button type="button" class="tier" data-copy="${esc(c.tier.code)}">` +
        `<span class="copy-swap"><code class="copy-idle">${esc(c.tier.code)}</code><span class="copy-done">${esc(T.copy_done)}</span></span></button>`;
    } else if (c.tier) {
      code = `<span>${esc(T.code_none)}</span>`;
    } else if (c.shortfall) {
      code = `<span>${esc(fmt(T.tier_short, { m: whole(c.picked.min_spend_usd), g: usd(c.shortfall) }))}</span>`;
    }
    let hint = '';
    if (c.price && c.choice === 'auto' && c.next) {
      hint = `<p class="field-hint">${esc(fmt(T.next_tier, { g: usd(c.next.min_spend_usd - c.subtotal), m: whole(c.next.min_spend_usd), o: whole(c.next.off_usd) }))}</p>`;
    }

    let msrp = '';
    if (p && c.price) {
      const diff = r2(p.msrp_usd - c.net);
      const pct = Math.abs(Math.round(diff / p.msrp_usd * 1000) / 10);
      const tpl = diff >= 0 ? T.msrp_low : T.msrp_high;
      msrp = `<p class="calc-msrp" data-vs-msrp>${esc(fmt(tpl, { m: usd(p.msrp_usd), d: usd(Math.abs(diff)), p: pct }))} <span>${esc(T.msrp_note)}</span></p>`;
    }

    const krwLine = rate ? `<span class="krw num" data-net-krw>${esc(fmt(T.approx_krw, { v: Math.round(c.net * rate).toLocaleString('ko-KR') }))}</span>` : '';
    const go = p
      ? `<p class="calc-go-name">${esc(p.name)}</p><div class="calc-cta">` +
        `<a class="btn btn-ali is-first" data-aff="ali" data-store="aliexpress" data-pid="${esc(p.id)}" href="${esc(p.ali)}" target="_blank" rel="nofollow sponsored noopener"><span class="sdot"></span>${esc(T.btn_ali)}</a>` +
        `<a class="btn btn-${esc(D.dom_cls)}" data-aff="dom" data-store="${esc(D.dom_cls)}" data-pid="${esc(p.id)}" href="${esc(p.dom)}" target="_blank" rel="nofollow sponsored noopener"><span class="sdot"></span>${esc(T.btn_dom)}</a>` +
        `</div><p class="calc-go-more"><a class="text-link" href="../../p/${esc(p.slug)}/">${esc(T.detail)}</a></p><p class="btn-disc">${esc(T.btn_disc)}</p>`
      : `<p class="field-hint">${esc(T.go_hint)}</p>`;

    out.innerHTML =
      `<div class="sheet calc-sum"><h2>${esc(T.sum_h)}</h2>` +
      `<p class="calc-net"><span class="usd num" data-net-usd>${usd(c.net)}</span>${krwLine}</p>` +
      `<dl class="calc-lines num">${lines.join('')}</dl>` +
      (code ? `<p class="calc-code">${code}</p>` : '') + hint + msrp + `</div>` +
      customsBox(c) +
      `<div class="sheet calc-go"><h2>${esc(T.go_h)}</h2>${go}</div>`;
    if (window.__gchApplyAttribution) window.__gchApplyAttribution(out);
  }

  f.preset.addEventListener('change', () => {
    const p = byId[f.preset.value];
    if (p) {
      f.price.value = p.msrp_usd;
      if (f.origin.querySelector('option[value="cn"]')) f.origin.value = 'cn';
      track('promo_preset', { pid: p.id });
    }
    render();
  });
  [f.price, f.coupon, f.coin, f.custom, f.rate].forEach(el => { if (el) el.addEventListener('input', render); });
  [f.tier, f.origin].forEach(el => el.addEventListener('change', render));

  const params = new URLSearchParams(location.search);
  const want = params.get('p');
  if (want && byId[want]) {
    f.preset.value = want;
    f.price.value = byId[want].msrp_usd;
  }
  track('tool_view', { tool: 'ali-promo-calculator' });
  render();
})();
"""


def render_promo_calculator_page(
    *,
    lang: str,
    items: list[dict],
    cfg: dict,
    promo_data: dict,
    head_fn: Callable[..., str],
    legal_fn: Callable[[str], str],
    header_fn: Callable[[str, str, dict, str], str],
    footer_fn: Callable[[str, str, dict], str],
    icon_fn: Callable[..., str],
    cat_label_fn: Callable[[str, str], str],
    name_fn: Callable[[dict], str],
    slug_fn: Callable[[str], str],
    now: datetime | None = None,
) -> str:
    up = "../../../"
    other = "en" if lang == "ko" else "ko"
    path = f"/{lang}/tools/ali-promo-calculator/"
    brand = cfg["site"]["brand_name"]
    dom_key = "coupang" if lang == "ko" else "amazon"
    notice = (promo_data.get("notice") or {}).get(lang, "")
    ref = active_promo({**promo_data, "events": []}, lang, sale_reference_date(lang, now))

    products = [
        {
            "id": it["id"],
            "slug": slug_fn(it["id"]),
            "name": name_fn(it),
            "msrp_usd": float(it.get("msrp_usd") or 0),
            "dom": it["affiliate_links"][dom_key],
            "ali": it["affiliate_links"]["aliexpress"],
        }
        for it in items
        if float(it.get("msrp_usd") or 0) > 0
    ]
    by_cat: dict[str, list[dict]] = {}
    for it in sorted(items, key=lambda x: (cat_label_fn(x["category"], lang), name_fn(x).lower())):
        if float(it.get("msrp_usd") or 0) > 0:
            by_cat.setdefault(cat_label_fn(it["category"], lang), []).append(it)

    if lang == "ko":
        title = f"알리익스프레스 프로모 코드 체감가·통관 계산기 ($150·$200 면세선) | {brand}"
        desc = "스토어 쿠폰·코인·프로모 코드 구간을 적용한 알리 예상 결제가와 대한민국 통관 면세선($150 / 미국발 $200) 여유를 실시간으로 계산하고 쿠팡 현재가와 바로 대조합니다."
        h1 = "알리 프로모 코드 체감가·통관 계산기"
        lead = "장바구니 금액에 코인 할인, 스토어 쿠폰, 프로모 코드 구간을 순서대로 적용해 예상 결제가를 계산하고 면세선까지 남은 여유를 알려 줍니다. 검수 제품을 고르면 제조사 출시 참고가가 입력되니, 실제 판매 페이지 가격으로 고쳐 쓰세요."
        crumb, home, form_lbl, out_lbl = "알리 코드·통관 계산기", "홈", "계산 조건 입력", "계산 결과"
        lbl = {
            "preset": "검수 제품 프리셋", "preset_none": "직접 입력 (임의 장바구니 금액)",
            "preset_hint": "선택하면 제조사 출시 참고가(MSRP)가 표시가에 입력됩니다. 실제 판매가가 아니므로 판매 페이지 가격으로 고쳐 쓰세요.",
            "price": "표시가 (USD)", "coupon": "판매자 스토어 쿠폰 (USD)", "coin": "코인 할인 (%)",
            "tier": "프로모 코드 구간", "custom": "직접 입력 코드 할인액 (USD)",
            "rate": "환율 (원/USD)", "rate_hint": "직접 수정할 수 있습니다. 기본값 1,400원.",
            "origin": "발송지·통관 기준",
        }
        origin_opts = [("cn", "중국·기타발 한국 수령 $150 면세"), ("us", "미국발 목록통관 $200 면세")]
        t_data = {
            "sum_h": "예상 결제가", "approx_krw": "약 {v}원",
            "l_price": "표시가", "l_coin": "코인 할인 ({p}%)", "l_coupon": "스토어 쿠폰",
            "l_tier": "프로모 코드 ({m} 이상 구간)", "l_custom": "프로모 코드 (직접 입력)",
            "tier_auto": "자동 · 최적 구간 적용", "tier_none": "적용 안 함", "tier_custom": "직접 입력",
            "tier_opt": "{m} 이상 −{o}",
            "code_lbl": "적용 코드", "copy_done": "복사됨 ✓",
            "code_none": "이 구간은 확인된 코드가 없습니다. 알리 행사 페이지의 코드를 결제창에 입력하세요.",
            "tier_short": "선택한 구간은 쿠폰 적용 후 금액이 {m} 이상이어야 합니다. {g} 부족합니다.",
            "next_tier": "{g} 더 담으면 {m} 이상 구간(−{o})이 열립니다.",
            "msrp_low": "제조사 출시 참고가 {m} 대비 {d} 낮음 ({p}%).",
            "msrp_high": "제조사 출시 참고가 {m} 대비 {d} 높음 ({p}%).",
            "msrp_note": "참고가는 실제 판매가가 아닙니다.",
            "empty_badge": "금액 입력 대기", "empty_head": "표시가를 입력하면 면세선 판정이 표시됩니다",
            "ok_badge": "면세 안전권 ({g} 여유)", "ok_head": "{t} 면세선 이내입니다",
            "ok_body_cn": "중국·기타국발은 물품가 미화 $150 이하일 때 관세·부가세가 면제됩니다. 같은 날 입항하는 다른 주문과 합산되면 면세선을 넘을 수 있으니 주문일을 나누세요.",
            "ok_body_us": "미국발 목록통관 적격 품목은 미화 $200 이하까지 면세입니다. 일반통관 대상 품목은 $150 기준이 적용되니 품목 분류를 확인하세요.",
            "warn_badge": "관부가세 부과 구간 — {t} 면세선 {g} 초과",
            "warn_head": "예상 부가세 약 {v} (과세가격의 약 10%)",
            "warn_body": "면세선을 넘으면 초과분이 아니라 물품가 전체에 부가세 약 10%가 붙고, 품목에 따라 관세가 더해집니다. 쿠폰·코드 적용 후 결제가를 {t} 이하로 맞추면 면세이며, 지금 기준 {g}만 더 낮추면 됩니다.",
            "go_h": "양쪽 판매처 실결제가 대조",
            "go_hint": "프리셋에서 검수 제품을 고르면 알리·쿠팡 판매처 버튼이 열립니다.",
            "btn_ali": "알리 프로모션·직구 확인", "btn_dom": "쿠팡 로켓 현재가 대조",
            "detail": "상세 스펙·단점 보기", "btn_disc": BUTTON_DISCLOSURE_KO,
        }
        foot_note = "계산 결과는 입력값 기준의 추정치입니다. 실제 과세가격은 관세청 고시환율, 배송비 포함 여부, 합산과세에 따라 달라지므로 결제창과 통관 안내를 최종 기준으로 삼으세요. 이 페이지는 판매처 가격을 저장하거나 표시하지 않습니다."
    else:
        title = f"AliExpress Promo Code & Customs Calculator (Coupon, Coins, Code Tiers) | {brand}"
        desc = "Stack a store coupon, coin discount and the promo-code tier on any cart amount, see the estimated checkout total, and compare AliExpress against Amazon US for 69 vetted models."
        desc = desc.replace("69 vetted", f"{len(products)} vetted")
        h1 = "AliExpress Promo & Customs Calculator"
        lead = "Apply the coin discount, the seller store coupon and the promo-code tier in order to estimate your checkout total, then see whether an import line applies. Picking a vetted model fills in its manufacturer reference MSRP; replace it with the live listing price."
        crumb, home, form_lbl, out_lbl = "Promo & Customs Calculator", "Home", "Calculator inputs", "Calculator result"
        lbl = {
            "preset": "Vetted product preset", "preset_none": "Custom cart amount",
            "preset_hint": "Selecting a model fills the list price with its manufacturer reference MSRP, which is not a store price. Replace it with the live listing price.",
            "price": "List price (USD)", "coupon": "Seller store coupon (USD)", "coin": "Coin discount (%)",
            "tier": "Promo-code tier", "custom": "Custom code amount (USD)",
            "origin": "Fulfillment origin",
        }
        origin_opts = [("domestic", "US Domestic Warehouse"), ("cross", "Cross-Border Direct Import")]
        t_data = {
            "sum_h": "Estimated checkout", "approx_krw": "",
            "l_price": "List price", "l_coin": "Coin discount ({p}%)", "l_coupon": "Store coupon",
            "l_tier": "Promo code ({m}+ tier)", "l_custom": "Promo code (custom amount)",
            "tier_auto": "Auto · best eligible tier", "tier_none": "No promo code", "tier_custom": "Custom amount",
            "tier_opt": "{m}+ saves {o}",
            "code_lbl": "Code for this tier", "copy_done": "Copied ✓",
            "code_none": "No confirmed code for this tier. Enter the code from the AliExpress sale page at checkout.",
            "tier_short": "That tier needs a post-coupon subtotal of {m} or more. You are {g} short.",
            "next_tier": "Add {g} more to reach the {m}+ tier ({o} off).",
            "msrp_low": "{d} below the manufacturer reference MSRP of {m} ({p}%).",
            "msrp_high": "{d} above the manufacturer reference MSRP of {m} ({p}%).",
            "msrp_note": "The MSRP is a launch reference, not a store price.",
            "empty_badge": "Waiting for an amount", "empty_head": "Enter a list price to see the import check",
            "dom_badge": "No import entry · US warehouse",
            "dom_head": "Ships domestically, so no customs line applies",
            "dom_body": "Orders fulfilled from a US warehouse are not import entries. Confirm the listing shows a US ship-from location before paying.",
            "cross_badge": "Import duties apply · cross-border",
            "cross_head": "De minimis ended: duties apply at every order value",
            "cross_body": "Since the US de minimis exemption ended, cross-border parcels owe duties regardless of value. Check that checkout shows 'Import charges included'; this estimate excludes any duty not shown there.",
            "go_h": "Compare both stores at checkout",
            "go_hint": "Pick a vetted model in the preset to open its AliExpress and Amazon US store buttons.",
            "btn_ali": "Check AliExpress Store", "btn_dom": "Check Amazon US Prime",
            "detail": "Full specs & caveats", "btn_disc": BUTTON_DISCLOSURE_EN,
        }
        foot_note = "Results are estimates from the values you enter. Sales tax, shipping and any duty not shown at checkout are excluded. This page never stores or displays retailer prices."

    def opt_group(cat_label: str, group: list[dict]) -> str:
        opts = "".join(f'<option value="{_esc(it["id"])}">{_esc(name_fn(it))}</option>' for it in group)
        return f'<optgroup label="{_esc(cat_label)}">{opts}</optgroup>'

    preset_opts = f'<option value="">{_esc(lbl["preset_none"])}</option>' + "".join(
        opt_group(c, grp) for c, grp in by_cat.items()
    )
    chev = icon_fn("down", 16)

    def money_field(name: str, label: str, unit: str, value: str, suffix: bool = False, step: str = "0.01",
                    hint: str = "", extra: str = "") -> str:
        hint_html = f'<span class="field-hint">{_esc(hint)}</span>' if hint else ""
        return (
            f'<li class="field"{extra}><label for="pc-{name}">{_esc(label)}</label>'
            f'<span class="inp{" is-suffix" if suffix else ""}"><span class="unit" aria-hidden="true">{unit}</span>'
            f'<input id="pc-{name}" name="{name}" type="number" inputmode="decimal" min="0" step="{step}" value="{value}" autocomplete="off"></span>'
            f'{hint_html}</li>'
        )

    rate_field = (
        money_field("rate", lbl["rate"], "원", str(DEFAULT_KRW_PER_USD), suffix=True, step="1", hint=lbl["rate_hint"])
        if lang == "ko" else ""
    )
    origin_html = "".join(f'<option value="{k}">{_esc(v)}</option>' for k, v in origin_opts)

    payload = json.dumps(
        {
            "lang": lang,
            "tz": SALE_TZ_HOURS[lang],
            "dom_cls": dom_key,
            "t": t_data,
            "ref": {"label": ref["label"], "source": ref["source"], "tiers": ref["tiers"]},
            "events": promo_events_for_lang(promo_data, lang),
            "products": products,
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    body = f"""
<body class="{lang}">
  {legal_fn(lang)}
  {header_fn(lang, up, cfg, f"{up}{other}/tools/ali-promo-calculator/")}
  <main class="wrap" data-promo-tool data-lang="{lang}">
    <nav aria-label="{'이동 경로' if lang == 'ko' else 'Breadcrumb'}">
      <ol class="crumbs">
        <li><a href="../../">{home}</a></li>
        <li> / </li>
        <li aria-current="page">{crumb}</li>
      </ol>
    </nav>
    <header class="page-head tool-hero">
      <h1>{_esc(h1)}</h1>
      <p class="dek">{_esc(lead)}</p>
    </header>

    <div class="calc">
      <section class="sheet tool-form" aria-label="{form_lbl}">
        <ul class="calc-fields">
          <li class="field is-wide"><label for="pc-preset">{_esc(lbl['preset'])}</label>
            <span class="sel"><select id="pc-preset" name="preset">{preset_opts}</select>{chev}</span>
            <span class="field-hint">{_esc(lbl['preset_hint'])}</span></li>
          {money_field("price", lbl["price"], "$", "")}
          {money_field("coupon", lbl["coupon"], "$", "")}
          {money_field("coin", lbl["coin"], "%", "", suffix=True, step="0.1")}
          <li class="field"><label for="pc-tier">{_esc(lbl['tier'])}</label>
            <span class="sel"><select id="pc-tier" name="tier"><option value="auto"></option></select>{chev}</span></li>
          {money_field("custom", lbl["custom"], "$", "", extra=" data-custom-wrap hidden")}
          {rate_field}
          <li class="field{' is-wide' if lang == 'en' else ''}"><label for="pc-origin">{_esc(lbl['origin'])}</label>
            <span class="sel"><select id="pc-origin" name="origin">{origin_html}</select>{chev}</span></li>
        </ul>
        <p class="calc-source"><span data-tier-source></span></p>
        <p class="board-note">{icon_fn('caution', 14)} {_esc(notice)}</p>
      </section>

      <section class="calc-out" data-promo-result aria-live="polite" aria-label="{out_lbl}"></section>
    </div>

    <p class="tool-foot-note">{_esc(foot_note)}</p>
    <script type="application/json" data-promo-json>{payload}</script>
  </main>
  {footer_fn(lang, up, cfg)}
  <script src="{up}assets/app.js" defer></script>
  <script>{PROMO_TOOL_JS}</script>
</body>
</html>
"""
    return head_fn(
        lang=lang, title=title, description=desc, up=up, cfg=cfg, path=path,
        alternates={"ko": "/ko/tools/ali-promo-calculator/", "en": "/en/tools/ali-promo-calculator/"},
    ) + body
