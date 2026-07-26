FROM ghcr.io/astral-sh/uv:python3.12-trixie

# nuxbt needs bluetoothd started without the systemd sandboxing that blocks
# raw HID access; an empty override file disables the upstream hardening.
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

USER root
