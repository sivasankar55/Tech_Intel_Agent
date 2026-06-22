#!/bin/bash
set -e

cd "$(dirname "$0")"

mkdir -p data exports logs

# Run initial collection on startup
python main.py --run-once

# Run daemon + dashboard in a single process (avoids SQLite locking)
python main.py --serve --port "${PORT:-8080}"
