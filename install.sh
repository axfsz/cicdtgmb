#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已生成 .env，请先编辑 .env 后再执行：docker compose up -d --build"
  exit 0
fi

docker compose up -d --build
docker logs -f ugtesta-tgmb
