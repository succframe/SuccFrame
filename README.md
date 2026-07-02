# SuccFrame

A desktop companion app for [Warframe](https://www.warframe.com/) — live world state, item search, market price checking, relic planning, and riven grading, all in one window.

## Features

- **World State** — Live planetary cycle timers (Earth, Cetus, Orb Vallis, Cambion Drift, Zariman, Duviri), void fissures, invasions, sorties, Baro Ki'Teer, and more.
- **Search Item** — Look up any item's stats, drop locations, and rarities.
- **Price Checker** — Live buy/sell orders from warframe.market.
- **Relic Planner** — Relic reward tables with market prices.
- **Riven Mods** — Grade your rivens, scout live auctions, and get a recommended sell price.

## Download

Grab the latest **`SuccFrame.exe`** from the [Releases page](https://github.com/succframe/SuccFrame/releases/latest). No installation needed — just run it. Python is **not** required.

> **Antivirus note:** Some antivirus tools flag PyInstaller-built exes as suspicious. This is a common false positive. If you'd rather not trust the exe, run from source instead (below).

## Run from source

Requires [Python 3.11+](https://www.python.org/downloads/).

```bash
pip install -r requirements.txt
python main.py
```

## Build the exe yourself

```bash
build.bat
```

The finished exe lands in the `dist` folder.

## Data sources

SuccFrame pulls live data from public community APIs — [warframestat.us](https://docs.warframestat.us/), [warframe.market](https://warframe.market/), and the open-source [warframe-riven-info](https://github.com/calamity-inc/warframe-riven-info) parser. It stores nothing but your local UI preferences.

This is a fan-made tool and is not affiliated with Digital Extremes or Warframe.
