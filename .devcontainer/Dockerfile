FROM ghcr.io/astral-sh/uv:debian-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
	curl \
	git \
	&& rm -rf /var/lib/apt/lists/* \
	sudo \
	bash \
	build-essential \
	lidbus-1-dev \
	libdbus-glib-1-dev


USER root