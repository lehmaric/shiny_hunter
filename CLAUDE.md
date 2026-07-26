# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A bot that plays Pokémon on a physical Nintendo Switch to hunt shiny Pokémon. It emulates a Pro Controller over Bluetooth (via `nuxbt`) while reading the console's HDMI output through a USB capture card, and uses OpenCV pixel thresholding to decide when an encounter started and whether the Pokémon is shiny.

Because it drives real hardware, most behaviour cannot be verified without a Switch, a capture card, and a Bluetooth adapter attached. There are no tests and no linter configured — changes are validated by running the bot.

## Commands

```bash
uv sync                      # install deps (run inside the devcontainer — pygobject needs cairo/girepository headers)
uv run switchBot.py          # run the bot (must be root — nuxbt needs raw Bluetooth access)
v4l2-ctl --list-devices      # find the capture card's /dev/videoN node
```

Debugging aids:
- `LIVE_PREVIEW = True` in `config.py` serves an MJPEG stream of the analysed frames at `http://localhost:8765` (`PREVIEW_PORT`). The devcontainer uses `network_mode: host`, so no port mapping is needed.
- FFmpeg's stderr goes to `ffmpeg.log` (overwritten on each capture start). If the stream never produces a first frame, that file has the reason.
- `DEBUGGING = True` raises log level to DEBUG and saves a timestamped PNG after *every* sequence event into `screenshots/debug/`.
- `SKIP_BLUETOOTH_SETUP = True` skips `bluetoothctl` configuration for dev machines without a usable adapter.

## Runtime environment

Development happens in the devcontainer (`.devcontainer/`): a `uv` + Debian **trixie** image with `bluez`, `ffmpeg`, and `v4l-utils`, run `privileged` with host networking, the host D-Bus socket mounted, and `/dev/hci0` plus the capture card's video nodes passed through. nuxbt talks to BlueZ over D-Bus and needs all of that.

The image also installs neovim, which is not a project dependency: `devcontainer-cli.nvim` connects by quitting the host editor and running `nvim` *inside* the container, so the binary has to be present or the connect silently collapses into "the editor just quit". Don't remove it as unused. It is pinned via the `NVIM_VERSION` build arg and should track the host version.

The base image must stay on trixie or newer. nuxbt pulls in `pygobject`, which is sdist-only and builds against `girepository-2.0` requiring **glib >= 2.80**; bookworm ships glib 2.74, so a bookworm base cannot satisfy it. An earlier iteration tried to bridge that by adding Debian sid to `sources.list.d/` plus `apt-get dist-upgrade` and `--force-overwrite`; that mixed-suite setup broke and was removed. Do not reintroduce it — bump the base image instead. The relevant build deps are `libgirepository-2.0-dev` (note: *not* `libgirepository-1.0-dev`, which is the legacy introspection package and only needed by pygobject's test subproject) and `libcairo2-dev` for `pycairo`.

`FFMPEG_INPUT_DEVICE` in `config.py` must match the device the capture card actually exposes, and that node must also be listed under `devices:` in `.devcontainer/docker-compose.yml`. These drift apart in practice — check both before debugging a "stream failed" error. Detecting the node automatically is an open TODO in `README.md`.

## Architecture

`switchBot.py` is the entry point and the only place with global state and orchestration; everything else is a package with a single class exported via `__init__.py`:

- `capture/` — `FrameCaptureManager` spawns FFmpeg (`v4l2` → downscale to 640×360 → `bgr24` rawvideo on stdout) and a daemon reader thread that keeps only the **latest** frame under a lock. `get_frame()` returns a copy. There is no frame queue; analysis always sees the newest frame, and a watchdog thread in `switchBot.py` restarts FFmpeg if the process dies.
- `controller/` — `ControllerManager` wraps nuxbt: `bluetoothctl` setup, controller creation/pairing, reconnect (via `get_switch_addresses()`), and name→`Buttons` mapping. `press_buttons()` blocks until the macro completes, then sleeps an extra `delay`. `cleanup()` force-terminates nuxbt's child processes to avoid an `atexit` assertion on shutdown.
- `processing/` — `ImageAnalyzer`, all static methods. Every detector is the same pipeline: crop by normalized (0–1) region → grayscale → Gaussian blur → binary threshold → *percentage of white pixels* compared against a threshold. **Polarity is not uniform**: `check_encounter_loaded`, `check_shiny_early_detection`, and `check_shiny_summary_star` invert the comparison (low white % means the thing is present), while the encounter-in-progress and battle checks do not. Read the specific method before adjusting a number.
- `game/` — `SequenceLoader`/`Sequence` (CSV loading + event validation) and `GameMacroExecutor` (hardcoded multi-press macros: `start_game`, `reset_position`, `save_game`). `reset_position` is a fragile chain of `Timings.RESET_POSITION_PHASE_*` sleeps with small random jitter; its purpose is soft-resetting the game back to the hunting spot.
- `config.py` — the single tuning surface: crop regions, thresholds, and every timing constant. Prefer changing values here over hardcoding them in the modules.

### The sequence DSL

`sequences.csv` (`game,method,sequence`, whitespace-separated tokens) defines what the bot does per hunt. Tokens:

- **buttons**: `a b x y up down left right l r zl zr plus minus home capture`
- **floats**: `2.4` → `time.sleep(2.4)`
- **events**: `loop`/`end` (repeat the enclosed tokens until an `encounter` check inside the block succeeds, max 50 iterations), `encounter` (black-screen detection), `battle` (poll until battle UI appears), `check` (early-animation shiny check), `summary` (shiny star on the summary screen), `reset` (run `reset_position`)

The interpreter is inline in `hunt_shiny()` in `switchBot.py` — a token that is neither a known event nor parseable as a float falls through to a button lookup, and unknown tokens are only warned about. Adding a new event means touching three places: `SequenceEventType` in `config.py` (validation), `Sequence._get_valid_buttons`/`_validate_events` if it is button-like, and the dispatch chain in `hunt_shiny()`.

`block_direction` (asked for interactively at startup, also a CSV column) suppresses one direction inside `loop` blocks so the player doesn't wander out of the grass.

### Operating procedure

The bot assumes a specific starting state, per `README.md`: be in position in-game, save, leave the pause menu hovering over Pokédex, then press Home and enter *Change Grip/Order* before starting the bot. On first pair you may need `bluetoothctl` open in another shell to answer `yes`. When a shiny is found the bot screenshots, disconnects the controller so you can catch it manually, and waits for `Y` on stdin before reconnecting.

## nuxbt input reliability (why >= 3.3.6)

`nuxbt` is a plain PyPI dependency pinned to `>=3.3.6`. That floor matters: older releases cached the last HID report and only re-sent it on state change, so a button press was carried by a *single* packet at 132 ticks/second — fragile enough that inputs got dropped and sequences desynced. Since 3.3.6, `controller/server.py` sends every tick while `input.active_input_queued()` is true, giving a held button a continuous stream of reports the Switch reliably polls.

Background on why that matters: Bluetooth Classic is reliable at the transport level (ACL links ACK and retransmit in hardware), so dropped inputs were never packets lost in the air. The problem was that the Switch expects a continuous ~132 Hz report stream and holds the last known state otherwise — a state change carried by exactly one packet can land outside its polling window. Sending on every tick while input is active removes that fragility.

This fix originated in this project as a local patch to a vendored copy under `vendor/nuxbt-src/` and was upstreamed; the vendored tree no longer exists. If input-dropping symptoms reappear, check the installed nuxbt version first.

## Known rough edges

- `save_highlight()` concatenates `shinyFound*.ts` segments, but the current FFmpeg command only pipes rawvideo and never writes those segments (`ROLLING_FILE` is unused) — it always logs "No video segments found".
- `check_if_in_encounter()` in `switchBot.py` reads the crop region as `Timings.__dict__["CropRegions.ENCOUNTER_DETECTION"]`, which raises `KeyError` on the debug save path.
- `RTSP_URL` in `config.py` is vestigial; `README.md`'s RTSP instructions predate the switch to direct v4l2 capture.
- `GameMacroExecutor.wait_for_encounter_load()` is a stub that just sleeps for 30 seconds.
- `README.md`'s TODO list is in German and is the closest thing to a roadmap.
