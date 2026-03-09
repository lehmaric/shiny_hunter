FROM ghcr.io/astral-sh/uv:python3.12-bookworm

RUN mkdir -p /run/systemd/system/bluetooth.service.d/ && touch /run/systemd/system/bluetooth.service.d/nuxbt.conf && \
	touch /etc/apt/sources.list.d/sid.list && echo "deb http://deb.debian.org/debian sid main" > /etc/apt/sources.list.d/sid.list

RUN apt-get update && apt-get install -y --no-install-recommends \
	curl \
	git \
	sudo \
	bash \
	build-essential \
	cmake \
	libdbus-1-dev \
	libdbus-glib-1-dev \ 
	libbluetooth-dev \
	bluez \
	libdbus-glib-1-dev \
	libdbus-1-dev \
	libcairo2-dev \
	libgirepository-2.0-dev \
	pkg-config \
	&& rm -rf /var/lib/apt/lists/*

USER root