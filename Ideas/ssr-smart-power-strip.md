
## Idea
4-channel Swiss smart power strip — gut a certified Type J (SEV 1011) 4-way strip and replace internals with SSRs + ESP32 + per-channel energy monitoring, exposed in Home Assistant via ESPHome.

## Why
- Hands-on project to experiment with solid state relays
- Silent switching, handles inductive/surge loads better than cheap smart plugs
- Per-outlet energy visibility → automations like "turn off idle devices", cost tracking, solar-surplus scheduling
- Keeps the certified socket block, cord, plug, strain relief → safer than a scratch mains build

## Constraints
- Switzerland: 230 V / 50 Hz, Type J SEV 1011, 10 A per socket
- Wire colours: L=brown, N=blue, PE=green/yellow
- Legal: plug-connected self-built appliance is fine for personal use; permanent wiring would need a licensed electrician (NIV)
- Must test through RCD (FI), ideally 10 mA for bench work
- SSRs need heatsinking — ~1.5 V drop × load current in heat
- Avoid counterfeit Fotek SSRs — use Crydom or Omron

## Possible approaches
**Chosen direction: gut a donor Swiss strip**
- Donor: Steffen or Brennenstuhl CH 4×T13 strip with roomy housing
- 4× Crydom D2425 or Omron G3NA-210B zero-cross SSRs (25 A, heatsinked)
- 4× PZEM-004T v3.0 on a shared UART bus (Modbus addresses 1–4) for per-channel V/A/W/kWh
- ESP32 DevKit running ESPHome, powered by HLK-PM03 (230 VAC → 3.3 VDC isolated)
- WAGO 221 lever nuts for mains joints; 1.5 mm² H05V-K wire

**Alternatives considered**
- Build-from-scratch in project box — more work, less neat
- DIN-rail in sub-panel — cleanest but needs electrician for permanent install
- Whole-strip metering instead of per-channel — cheaper but loses the interesting automations

## Rough BOM / cost
- Donor strip (~CHF 20), ESP32 (~CHF 10), 4× SSR (~CHF 40), 4× PZEM-004T (~CHF 20), HLK-PM03 (~CHF 8), heatsinks + wire + WAGOs (~CHF 20) → **~CHF 80–120 total**

## Open questions
- Physical override buttons on the strip for when Wi-Fi/HA is down?
- Any channel needing >10 A (kettle, heater)? Would need bigger SSR + T23 socket on that channel.
- Keep the original rocker switch as a hard master-off?

## Next step
- When ready to start, promote to `Projects/🟢 SSR Smart Power Strip/` with `index.md` + `Hardware.md` + `Software.md` (ESPHome YAML sketch with PZEM Modbus + 4× GPIO switches is already drafted — see plan at `~/.claude/plans/i-would-like-to-quizzical-unicorn.md`)
- Order donor strip and SSRs to start bench work
