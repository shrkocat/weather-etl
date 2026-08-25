#!/usr/bin/env bash
# One-shot manual run of the pipeline from the project root.
# For scheduled runs, point cron or a CI scheduled workflow at this script.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Running weather ETL pipeline: $(date -u)"
python -m src.main "$@"
