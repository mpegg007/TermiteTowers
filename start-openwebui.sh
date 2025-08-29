#!/usr/bin/env bash
set -euxo pipefail

sudo docker rm -f openwebui-dev1 || true

sudo docker run -d \
  --name openwebui-dev1 \
  -e PORT=3000 \
  -p 3000:3000 \
  ghcr.io/open-webui/open-webui:main
