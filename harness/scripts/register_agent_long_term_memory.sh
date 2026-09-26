#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
python -m harness.scripts.register_agent_long_term_memory "$@"
