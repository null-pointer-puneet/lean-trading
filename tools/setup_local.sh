#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker Desktop and retry." >&2
  exit 1
fi

if ! command -v lean >/dev/null 2>&1; then
  echo "lean CLI not found. Install it with: pip install lean" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.9+ from https://www.python.org/" >&2
  exit 1
fi

if [[ ! -d data/market-hours || ! -d data/symbol-properties ]]; then
  echo
  echo "LEAN data folder not initialized. Bootstrapping with 'lean init'..."
  echo "(This works without a paid QuantConnect login.)"
  echo
  lean init
  echo
fi

python3 "$ROOT/tools/download_data.py"
echo
echo "Local backtest ready."
echo "Try: lean backtest strategies/example_momentum --open"
