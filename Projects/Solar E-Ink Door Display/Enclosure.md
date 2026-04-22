---
tags: [hardware, 3d-print, enclosure]
---

# Enclosure

[[index|← Project Overview]]

## Target Dimensions
- **Total depth: 20–22mm**

| Layer | Thickness |
|---|---|
| E-ink display + bezel | ~4mm |
| PCB + components (lying flat) | ~8–10mm |
| LiFePO4 pouch cell (beside board) | ~6mm |
| Back cover + air gap | ~3mm |

## Face Layout (top → bottom)
- E-ink display — ~80% of face area
- Bottom strip — 4 evenly-spaced buttons + WS2812B RGB LED centered between B2 and B3

## Side Panel Cutouts
- JST solar cable port
- USB-C passthrough for firmware flashing (optional)

## Back Plate
- 4× M3 heat-set inserts for wall mounting screws
- Lip/gasket groove around e-ink window for dust sealing

## Notes
- Solar panel mounted **separately** on window frame or door surround, angled toward light
- ESP32 dev board is thickest component — determines internal cavity depth
- CAD tool: FreeCAD / Fusion 360 / OpenSCAD (TBD)

## Next Steps
- [ ] Measure actual dev board dimensions
- [ ] Choose CAD tool
- [ ] Model enclosure shell
- [ ] Model button cutouts + LED window
- [ ] Model solar cable port + USB-C passthrough
- [ ] Print test fit (PLA), then final print (PETG for door environment)
