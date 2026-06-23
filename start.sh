#!/bin/bash
set -e

cd "$(dirname "$0")"

mkdir -p data exports logs

# Run initial collection on startup
python main.py --run-once

# Run both daemon (24h scheduler) and dashboard API
python main.py --daemon &
python main.py --dashboard --port "${PORT:-8080}"
