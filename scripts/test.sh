#!/usr/bin/env bash
set -euo pipefail

poetry run pytest --maxfail=1 --disable-warnings -q --cov=converter --cov-report=term-missing "$@"