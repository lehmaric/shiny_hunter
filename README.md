# Shiny Hunter

A bot that hunts shiny Pokémon on a real Nintendo Switch. It pretends to be a Pro Controller over Bluetooth ([nuxbt](https://pypi.org/project/nuxbt/)), watches the console's HDMI output through a USB capture card, and uses simple OpenCV pixel thresholds to detect encounters and shinies. When it finds one, it disconnects so you can catch it yourself.

## What you need

- A Nintendo Switch (docked, HDMI out)
- A USB capture card that shows up as a V4L2 device (tested with a UGREEN 15389)
- A Linux host with a Bluetooth adapter and BlueZ
- Docker (for the devcontainer)

## Setup

### 1. Prepare the host's Bluetooth service

nuxbt needs `bluetoothd` running with `--compat --noplugin=*`. Without it, BlueZ's input plugin grabs the Switch's connection and pairing hangs silently at *"Put your Switch in 'Pair New Controllers' mode"*. Run this **on the host** (not in the container — systemd lives on the host):

```bash
sudo mkdir -p /run/systemd/system/bluetooth.service.d
printf '[Service]\nExecStart=\nExecStart=/usr/libexec/bluetooth/bluetoothd --compat --noplugin=*\n' \
  | sudo tee /run/systemd/system/bluetooth.service.d/nuxbt.conf
sudo systemctl daemon-reload && sudo systemctl restart bluetooth
ps -eo args | grep [b]luetoothd     # should show --compat --noplugin=*
```

- The override lives in `/run`, so it is **gone after every reboot** — redo this step after restarting the host.
- While it is active, your other Bluetooth devices (keyboard, mouse, headphones) won't work. To undo: delete the file and run the `daemon-reload`/`restart` line again.
- The `bluetoothd` path can differ per distro; check `systemctl cat bluetooth.service | grep ExecStart`.

### 2. Start the devcontainer

Open the project in the devcontainer (`.devcontainer/`). It contains all build dependencies, so nothing extra needs to be installed on the host. The container runs privileged with host networking, the host's D-Bus socket, and the host's whole `/dev` mounted, so capture cards are visible even if plugged in later.

Inside the container:

```bash
uv sync
```

### 3. Point the bot at the capture card

```bash
v4l2-ctl --list-devices
```

```
UGREEN 15389: UGREEN 15389 (usb-0000:00:14.0-1.1.2):
        /dev/video14
        /dev/video15
        /dev/media2
```

Use the **first** `/dev/videoN` of the card (the second one carries no video) and set `FFMPEG_INPUT_DEVICE` in `config.py`. The number changes depending on what else is attached, so check it when capture fails.

Quick capture test (skips the first frames, which are often black):

```bash
ffmpeg -y -f v4l2 -i /dev/video14 -vf "select=gte(n\,30)" -frames:v 1 -update 1 test.png
```

If the image is completely black, the card gets no signal — re-seat the HDMI cable / dock connection and try again.

## Running a hunt

1. In the game: stand where you want to hunt (in grass, in front of a static encounter, …), **save**, and leave the pause menu hovering over **Pokédex**.
2. Press **Home** and open **Controllers → Change Grip/Order**.
3. Start the bot in the container:
   ```bash
   uv run switchBot.py
   ```
4. The controller pairs and the bot returns to the game. If pairing needs confirmation, open `bluetoothctl` in a second shell and type `yes`.
5. Answer the prompts:
   - **Game** and **Method** — must match a row in `sequences.csv` (the bot logs the available ones, e.g. `frlg` / `re`).
   - **Hunt target** — informational only.
   - **Block direction** — optional; a direction that is never pressed inside `loop` blocks, so the character can't walk out of the grass.
6. Watch it at <http://localhost:8765> (live preview of the analysed frames).

When a shiny is found the bot saves screenshots to `screenshots/`, disconnects the controller and waits. Catch it manually, then type `Y` to reconnect.

## Sequences

`sequences.csv` has one hunt per row: `game,method,sequence`. The sequence is a list of space-separated tokens:

| Token | Meaning |
|---|---|
| `a b x y up down left right l r zl zr plus minus home capture` | press that button |
| a number, e.g. `2.4` | wait that many seconds |
| `loop … end` | repeat the enclosed tokens until an `encounter` check inside them succeeds |
| `encounter` | check whether the screen went black (encounter transition); only meaningful inside `loop` |
| `battle` | wait until the battle menu is visible |
| `check` | shiny check during the encounter animation (Gen 3 layout) |
| `summary` | shiny check via the star on the summary screen |
| `reset` | soft-reset back to the saved position |

After a `loop` block finds an encounter, the bot waits until the battle scene has faded in, then continues with the tokens after `end`. The whole sequence repeats until a shiny is found.

Example (random encounters in FRLG — walk, check, run away):

```
frlg,re,loop left encounter right encounter up encounter down encounter end check 0.2 a 0.1 a 3.6 down right down right a a 0.5 a 4
```

## Configuration and debugging

All tuning lives in `config.py`: capture device, crop regions, brightness thresholds and every timing.

- `LIVE_PREVIEW = True` — MJPEG preview at `http://localhost:8765` (`PREVIEW_PORT`).
- `DEBUGGING = True` — debug logging plus a timestamped screenshot after every sequence step in `screenshots/debug/`.
- `SKIP_BLUETOOTH_SETUP = True` — skip the `bluetoothctl` setup (for machines without an adapter).
- `ffmpeg.log` — FFmpeg's output; look here if the stream never starts.
- Detection screenshots (`encounter_original.png`, `shiny_precheck.png`, …) in `screenshots/` show what the bot saw when it decided something.

### Troubleshooting

| Symptom | Likely cause |
|---|---|
| Hangs at *"Put your Switch in 'Pair New Controllers' mode"* | Host `bluetoothd` is missing `--compat --noplugin=*` (step 1; gone after reboot) |
| `Exception in thread … connection_reset_watchdog … UnknownObject` | Harmless race in nuxbt while discoverable; pairing continues |
| `Failed to register agent object` | Harmless; nuxbt registers its own agent first |
| `Stream failed, check ffmpeg.log` | Wrong `FFMPEG_INPUT_DEVICE` |
| Captured image is black | No HDMI signal reaching the card — re-seat the cable |
| Buttons get dropped, sequences desync | nuxbt older than 3.3.6 — `uv pip show nuxbt` |

## Running without the container

Possible, but it installs build headers on the host. On Ubuntu 24.04 / Pop!_OS (glib ≥ 2.80 is required):

```bash
sudo apt install libgirepository-2.0-dev libcairo2-dev pkg-config ffmpeg v4l-utils bluez
uv sync
sudo .venv/bin/python switchBot.py
```

## TODOs

### Capture

- [ ] Detect the capture device automatically via `v4l2-ctl --list-devices` (find the capture card by name, see `CONTEXT.md`)

### Bluetooth and controller

- [ ] Check at startup whether `bluetoothd` runs with `--compat --noplugin=*` and abort with a clear message instead of hanging silently while pairing
- [ ] Fix the race in nuxbt's watchdog (`find_connected_devices`, `UnknownObject`) upstream

### Sequences and input

- [ ] The reset sometimes only gets to the main menu and sometimes all the way to the starting point
- [ ] Only tap directions briefly inside `loop` blocks (e.g. 0.05–0.08 s) so the character just turns instead of walking — a separate hold time for direction buttons only; menu inputs keep `BUTTON_PRESS_DURATION`

### Detection

- [ ] Avoid a false encounter at game start: the black loading screen can be detected as an encounter

### Shiny handling

- [ ] Shiny highlight video: `save_highlight()` never finds segments because FFmpeg no longer writes `.ts` files

### Done

- [x] Figure out the right sequence for Nockchan
- [x] Add a stream for debugging sequences so the output can be watched (`LIVE_PREVIEW`)
- [x] Refactoring: split into several modules instead of one big main
- [x] Replace `print` with `logging`
