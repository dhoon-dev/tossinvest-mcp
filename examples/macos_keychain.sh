#!/usr/bin/env bash
set -euo pipefail

/usr/bin/security add-generic-password -U -a "$USER" -s tossinvest-api-key -w
/usr/bin/security add-generic-password -U -a "$USER" -s tossinvest-secret-key -w
