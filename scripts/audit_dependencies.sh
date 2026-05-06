#!/usr/bin/env bash
# Run dependency vulnerability scan (D1). Usage: ./scripts/audit_dependencies.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install --user pip-audit 2>/dev/null || python3 -m pip install pip-audit
python3 -m pip_audit -r requirements-prod.txt
