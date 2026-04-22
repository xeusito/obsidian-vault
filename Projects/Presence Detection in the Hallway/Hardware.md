# Hardware

## Components
- **ESP32 DevKit** — CP2102 USB-to-UART bridge, 3.3V logic
- **HLK-LD2450** — 24GHz mmWave radar, ±60° azimuth, 6m range, tracks up to 3 targets simultaneously

LD2450 IO level is 3.3V — matches ESP32 directly, no level shifter needed.

## Wiring

| LD2450 | Wire color | ESP32 |
|---|---|---|
| 5V | Black | VIN |
| GND | Yellow | GND |
| TX | White | RX2 (GPIO16) |
| RX | Red | TX2 (GPIO17) |

```mermaid
flowchart LR
    subgraph ESP32["ESP32 DevKit"]
        direction TB
        VIN["VIN (5V)"]
        G1["GND"]
        RX2["RX2 / GPIO16"]
        TX2["TX2 / GPIO17"]
        USB["USB-C (power in)"]
    end
    subgraph LD2450["HLK-LD2450"]
        direction TB
        V5["5V"]
        G2["GND"]
        TX["TX"]
        RX["RX"]
    end
    USB -.->|5V from host| VIN
    VIN ==>|black| V5
    G1 ==>|yellow| G2
    TX ==>|white| RX2
    TX2 ==>|red| RX
```

## Mounting
Mount the LD2450 vertically on the wall, ~1.5m high, facing down the hallway.
