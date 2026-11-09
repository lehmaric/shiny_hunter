FROM ghcr.io/astral-sh/uv:python3.12-trixie

# Marker only: nuxbt's CLI (`nuxbt test`, `demo`, `webapp`, ...) refuses to run
# unless this file exists. It changes nothing here — the container has no
# systemd. The real override (bluetoothd --compat --noplugin=*) must be applied
# on the HOST, under the same path, or pairing hangs. switchBot.py doesn't check.
RUN mkdir -p /run/systemd/system/bluetooth.service.d/ && \
	touch /run/systemd/system/bluetooth.service.d/nuxbt.conf

# libgirepository-2.0-dev + libcairo2-dev are build deps for pygobject/pycairo,
# which nuxbt pulls in to talk to BlueZ over D-Bus. pygobject >= 3.52 requires
# girepository-2.0 (glib >= 2.80), which is why this image is trixie and not
# bookworm (glib 2.74).
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
	curl \
	git \
	sudo \
	bash \
	build-essential \
	cmake \
	pkg-config \
	libdbus-1-dev \
	libdbus-glib-1-dev \
	libbluetooth-dev \
	bluez \
	libcairo2-dev \
	libgirepository-2.0-dev \
	libgl1 \
	ffmpeg \
	v4l-utils \
	&& rm -rf /var/lib/apt/lists/*

# devcontainer-cli.nvim connects by running `nvim` inside the container, so the
# binary has to exist here or the connect just exits. Installed from the
# upstream release rather than left to the dotfiles bootstrap, which is not
# reliable. Kept in step with the host version.
ARG NVIM_VERSION=v0.12.4
RUN curl -fsSL "https://github.com/neovim/neovim/releases/download/${NVIM_VERSION}/nvim-linux-x86_64.tar.gz" \
	| tar -xz -C /opt \
	&& ln -s /opt/nvim-linux-x86_64/bin/nvim /usr/local/bin/nvim \
	&& nvim --version | head -1

USER root
