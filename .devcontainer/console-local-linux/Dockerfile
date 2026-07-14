FROM mcr.microsoft.com/devcontainers/base:ubuntu

RUN apt-get update && apt-get install -y curl

RUN curl -fsSL https://pixi.sh/install.sh | PIXI_HOME=/usr/local bash

USER vscode
RUN mkdir -p /home/vscode/.cache/pixi