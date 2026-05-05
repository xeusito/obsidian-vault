---
status: resolved
date: 2026-05-05
tags: [raspberry-pi, home-lab, mikrotik, networking, troubleshooting]
---
# Raspberry Pi 4 won't connect to MikroTik 2.4 GHz when AX is enabled

**Affected device:** Raspberry Pi 4 Model B Rev 1.1 (BCM4345/6, firmware 7.45.265, Aug 2023)
**AP:** MikroTik cAP ax, RouterOS 7.22.2, `/interface/wifi`

## Symptom
Pi 4 failed to associate with the 2.4 GHz SSID when the cAP ax 2.4 GHz radio was configured for **2GHz-AX**. 5 GHz clients and other 2.4 GHz clients (phones, laptops, IoT) were unaffected.

## Root cause
The Cypress BCM4345/6 chip on the Pi 4 does not correctly handle HE (802.11ax) management frames on the 2.4 GHz band. Even though HE is nominally backwards-compatible, the Pi either fails to associate or drops shortly after when the AP advertises HE capabilities on 2.4 GHz.

This affects the entire Cypress/Broadcom family used across Raspberry Pi models (BCM43438, CYW43436, BCM4345/6) — it's a Pi Wi-Fi firmware limitation, not a MikroTik bug.

## Fix
On the MikroTik cAP ax, change the 2.4 GHz radio configuration from `2ghz-ax` to `2ghz-n`:

```
/interface/wifi/configuration
set [find name=<2g-config-name>] channel.band=2ghz-n
```

Or via Winbox: **WiFi → Configurations →** *(your 2.4 GHz profile)* **→ Channel → Band: `2ghz-n`** → Apply.

Pi associates immediately on next scan.

## Trade-off
2.4 GHz drops from AX (HE) back to N (HT). In practice this costs nothing meaningful — the band is too crowded and narrow for HE gains to matter, and all common 2.4 GHz clients (IoT, ESP32, older laptops) are N-only anyway. **5 GHz remains on AX**, which is where the real throughput lives.

## Verification
- Pi associates within ~5 s of boot.
- `iwconfig wlan0` on the Pi shows `IEEE 802.11`, link to expected BSSID.
- Other 2.4 GHz clients unaffected (phones, ESP-based sensors confirmed reconnecting).

## Diagnostic commands (Pi side)
```bash
cat /proc/device-tree/model          # Pi hardware model
dmesg | grep -i brcmfmac             # Wi-Fi chipset and firmware version
iw dev wlan0 link                    # current association state
```

## Related
- Affects all Raspberry Pi models with onboard Wi-Fi (Pi 3B+, 4, 5, Zero 2 W) — same Broadcom/Cypress family.
- Same workaround applies to other Cypress/Broadcom-based devices (some older Android tablets, some Smart TVs).
- If AX on 2.4 GHz is required in the future: attach an external USB Wi-Fi adapter with a chipset known to support HE properly (e.g. MediaTek MT7921).
- Revisit if a future Pi firmware update (`sudo rpi-update` / kernel package update) ships fixed brcmfmac firmware for HE on 2.4 GHz.
