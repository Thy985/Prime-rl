#!/usr/bin/env bash
# Run a swe-lab eval config against the Tencent router endpoint.
#   usage: bash tools/swe_lab/run_swe_eval.sh <config.toml> [extra eval args...]
set -uo pipefail
cd /home/lenovo/projects/prime-rl
set -a; . ./.env; set +a
export DUMMY_API_KEY="$TENXUN_API_KEY"
export PYTHONPATH=tools/swe_lab_env
export SWE_REAL_PY=/tmp/swe_deps/django_env/bin/python
# --no-sync: skip dependency resolution; deep-ep metadata fails on aarch64
exec uv run --no-sync eval @ "$@"
