FROM ghcr.io/astral-sh/uv:debian-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
	curl \
	git \
	&& rm -rf /var/lib/apt/lists/* \
	sudo \
	bash


USER root