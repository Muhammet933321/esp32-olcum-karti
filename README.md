# Ölçüm Kartı — a bench measurement card for ESP32-S3

A **voltmeter, ammeter, wattmeter, energy counter, oscilloscope and battery
capacity tester** on one board. ESP32-S3 + two 16-bit ADCs, driven entirely
from a web browser — from a phone with no computer involved, or from a PC
over USB.

> **Status: the design is verified, the hardware is not built yet.**
> Every number in this repository is computed or simulated, never typed by
> hand. Nothing here has been measured on a physical board. What that means
> in practice is spelled out in [What this repo does *not* prove](#what-this-repo-does-not-prove).

> **Language note.** The code comments, the engineering journal
> ([`DEVIR.md`](DEVIR.md)) and the user documentation ([`BELGELER/`](BELGELER))
> are in **Turkish** — that is the language this project was built in. This
> README is the English entry point. Türkçe rehber: [README.tr.md](README.tr.md).

---

## What it measures

| Capability | Range | Notes |
|---|---|---|
| **Voltage** — normal channel | ±32.4 V | bidirectional, referenced to an internal VREF |
| **Voltage** — high channel | ±613.7 V | 4.9 MΩ divider chain |
| **Current** | up to ±11.55 A | four shunt options: 10 / 1 / 0.1 / 0.015 Ω |
| **Power · energy** | V × I, signed | true power with per-range phase calibration |
| **Sample rate** | **665 Sa/s** | both channels sampled *simultaneously* (see below) |
| **Oscilloscope** | −63.5 … +46.8 V | 611 – 83 333 Sa/s, 28.8 mV step |
| **Battery test** | ≤ 38.5 V, 6.55 A | mAh **and** Wh, discharge curve, DC internal resistance |

The wattmeter is the reason for most of the engineering in here. Measuring
power correctly means the voltage and current samples must describe *the same
instant* and pass through *matched filters* — two things that turned out to be
false in earlier revisions and cost a large fraction of this project's effort
to fix.

## Three ways to connect

The board has no screen. It is used from a browser, and there are three paths
— all showing the same interface. Full explanation (in Turkish, with a
diagram) in [`BELGELER/6-ag.html`](BELGELER/6-ag.html).

| # | Mode | Address | When |
|---|---|---|---|
| 1 | **The board's own Wi-Fi** | `192.168.4.1` | No computer. The board serves the whole UI from its own flash |
| 2 | **Board on your home Wi-Fi** | `http://olcum.local` | Board is out of cable reach. Falls back to mode 1 after 10 s |
| 3 | **USB bridge** — *preferred, when USB is safe* | the address the bridge prints | A small Python program relays the board over USB and serves the UI |

**Why the bridge is preferred:** every browser connected directly to the board
slows the measurement down — the board runs both the sampling loop and an HTTP
server. Up to **4** browsers can watch the board directly; while a bridge is
registered, the board redirects direct clients to it, so only the bridge talks
to the board. Readings are archived on the PC instead of being limited by the
board's memory. The board's Wi-Fi does **not** turn itself off in this mode —
send `N0` over the serial console if you want the measurement loop left alone.

> ⚠️ **USB is not always an option.** The board is **not isolated**: with USB
> plugged in, the board's ground is your computer's ground. For a
> mains-referenced circuit you must run on battery + Wi-Fi with USB unplugged —
> i.e. mode 1. See [Safety](#safety).

## What's in this repository

| Path | What |
|---|---|
| [`kod/olcum-karti-a3/`](kod/olcum-karti-a3) | Firmware (Arduino / ESP32-S3). Measurement math, oscilloscope, battery test, web layer |
| [`sema3/`](sema3) | KiCad schematic — the design of record |
| [`arayuz3/`](arayuz3) | Web interface (Vue 3, no build step, vendored locally) |
| [`kopru/`](kopru) | PC bridge — serial↔SSE relay, disk archive, driver arbitration. Python standard library only |
| [`BELGELER/`](BELGELER) | **User documentation, generated** — HTML + PDF. Start at `index.html` |
| [`uretim/`](uretim) | The verification chain, simulations and every generator |
| [`uretim/_tezgah.md`](uretim/_tezgah.md) | **Generated** — the 72 things that must be measured once the hardware exists |
| [`DEVIR.md`](DEVIR.md) | Engineering journal. Long, chronological, Turkish — the record of how every decision was reached |
| [`arsiv/`](arsiv) | Earlier stages (ATmega328P, then a first ESP32 revision), each with its own chain |

## Building one

1. **Parts** — [`BELGELER/2-malzemeler.html`](BELGELER/2-malzemeler.html) is
   generated from the schematic, so it can't drift from the design.
2. **Assembly** — [`BELGELER/4-kurulum.html`](BELGELER/4-kurulum.html): seven
   steps, each ending in a measurement gate you must pass before continuing.
3. **Firmware** — open `kod/olcum-karti-a3/olcum-karti-a3.ino` in the Arduino
   IDE (ESP32 core 3.3.x, board `ESP32S3 Dev Module`, partition `huge_app`),
   or compile with `arduino-cli`. It builds warning-free with `-Wall -Wextra`.
4. **Interface onto the board** —
   `cd uretim && python arayuz-uret.py && python arayuz-yaz.py` packs the UI
   into a LittleFS image and flashes it at offset `0x310000`.
5. **PC bridge (optional)** — double-click `Kopru Baslat.bat`.

**Footprint:** firmware **1 067 423 B (33 % of flash)**, **71 420 B RAM
(21 %)**. The interface is **93 753 B** (7 assets, gzip-precompressed) inside a
917 504 B LittleFS partition.

## The verification chain

This is the part the project actually spends its time on. The design is
checked by a chain of runnable steps rather than by review:

```bash
cd uretim
python dogrula3.py     # current stage — 17 steps, ~6 min
python dogrula2.py     # archived stage 2
python dogrula.py      # archived stage 1
```

**17 steps, 1027 assertions.** Circuit behaviour is simulated with **ngspice**;
the firmware's measurement math is executed as *real compiled code* inside a
bit-verified **AVR emulator**; the schematic is checked node by node from the
netlist (ERC only says "connected", not "correct"); the firmware is compiled
with the real toolchain and the binary is searched for dead branches; and every
command the UI can send is compared against the `case` labels the firmware
actually implements.

The chain finishes by writing two files:

- **`uretim/_tezgah.md`** — the bench list (below).
- **`uretim/beklenen_sayim.json`** — an assertion-count lock. If a step's
  count changes **in either direction**, the chain goes red. Deliberate?
  `python dogrula3.py --sayim-kilidi-yaz`.

### A green test proves nothing

That sentence is this project's operating rule, and it was earned. Four times
the chain was fully green while something real and expensive was broken:

| Found | While the chain said |
|---|---|
| The web interface **never opened in a browser** — two assets 404'd | 15/15 green, UI tests 82/82 |
| The board sampled at **500 Sa/s, not 665** — `WebServer` calls `delay(1)` internally when idle, and `CONFIG_FREERTOS_HZ=1000` quantised the loop | 15/15 green |
| Phase calibration was stored in **samples** while correcting a fixed **time** — 1.74× the project's own error budget | 15/15 green |
| A bare `g` command **permanently bricked a channel** (gain 0 written to NVS, recovery threshold then unsatisfiable) | 15/15 green |

So the chain is not trusted on its own. Assertions are tested by **breaking
the source and checking that they turn red**:

```bash
python mutasyon.py                 # light mutations, ~15 s
python mutasyon.py --adim B22b     # target one step
python mutasyon.py --liste         # show what it would run
python mutasyon.py --adim B3       # runs the whole chain (~12 min):
python mutasyon.py --adim B23      # these two test the chain's OWN guards
```

Each mutation runs against a **copy** of the tree, never in place — this
project is not a git repo on the author's machine, so an interrupted in-place
mutation would have no way back. On the day it was built, the runner found
**three empty assertions** (one matched a substring so a renamed call still
passed; one constant had no assertion at all) and **two invisible
dependencies** that only appear when the project is run from a clean tree.

## What this repo does *not* prove

Everything here is computation and simulation. The board has never been built.
The chain therefore ends by generating **[`uretim/_tezgah.md`](uretim/_tezgah.md)** —
**72 measurements**, each written next to the code that *cannot* verify it,
with an acceptance criterion. **9 of them are marked for the first day**, among
them:

- the `+3V3` rail being back-fed through the clamps when USB is unplugged while
  the ±12 V supply is on — the calculated headroom is **18 mV**
- the sample count in the live data line: is it really ~133 per 200 ms?
- the battery-test failsafe: reset the board mid-discharge and confirm the load
  actually disconnects
- whether the interface renders correctly in a real browser at all

That list is generated, not maintained by hand — a step that stops declaring
its bench items turns the chain red.

## Requirements

| Tool | Used by |
|---|---|
| Python 3.14 (standard library only) | the whole chain, the bridge, all generators |
| [KiCad 10](https://www.kicad.org/) | schematic, ERC, netlist — and its bundled **ngspice** for every simulation |
| `arduino-cli` + ESP32 core 3.3.x | firmware compile step |
| `avr-gcc` (from the Arduino AVR package) | runs the measurement math as real code |
| Node.js | the interface / command-consistency step |

Two things live **outside** this repository and are expected to be missing on a
fresh clone — both are handled with an explicit message rather than a crash:

- `arduino-cli.exe`, looked up two directories above the project root
- the author's personal component inventory (`stok-takip/envanter.csv`), which
  the BOM step compares the design against. Without it, that comparison is
  announced as skipped; the assertion-count lock will then report a difference
  for that step, so run `python dogrula3.py --sayim-kilidi-yaz` once to set
  your own baseline.

Tool paths are currently hard-coded for Windows (`C:\Program Files\KiCad\10.0\bin`).

## Safety

**615 V is lethal, and this board is not isolated** — it is connected to your
computer over USB. Do not connect it to a mains-referenced circuit (for example
the primary side of a non-isolated SMPS) unless you understand exactly what
that means for every ground in the room. The assembly guide repeats this where
it matters, and the failure-mode analysis
([`uretim/sim3_ariza.py`](uretim/sim3_ariza.py), 111 assertions) quantifies
over 30 abuse scenarios — reverse voltage, overvoltage, supply loss, component
failure — against one acceptance criterion: *no single fault may kill the
ESP32 or the PC.*

Dangerous commands over the network (starting a battery discharge, writing
calibration) always require a session token plus a custom header, which stops
another web page from driving your board. A **password is optional and is not
set by default** — until you set one with `Ns<password>` over the serial
console, anyone who can reach the board on your network can send those
commands. The firmware says so loudly at boot.

**Stopping a discharge requires neither** — no token, no password, always.
Safety comes before convenience.
