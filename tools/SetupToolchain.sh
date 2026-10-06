#!/usr/bin/env bash
# SetupToolchain.sh, Version: 1.00
set -Eeuo pipefail
Mode="${1:---check}"
[[ $# -le 1 && ( "$Mode" == --check || "$Mode" == --install ) ]] || { echo "Usage: $0 [--check|--install]" >&2; exit 2; }
ToolDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
[[ "$(uname -s)" == Linux ]] || { echo 'Linux is required.' >&2; exit 1; }
: "${TAKEOVER_IDF_PATH:?Set TAKEOVER_IDF_PATH}"
: "${TAKEOVER_IDF_TOOLS_PATH:?Set TAKEOVER_IDF_TOOLS_PATH}"
for Tool in bash python3 git; do
  command -v "$Tool" >/dev/null || { echo "Missing tool: $Tool" >&2; exit 1; }
done
export IDF_TOOLS_PATH="$TAKEOVER_IDF_TOOLS_PATH"
if [[ "$Mode" == --install ]]; then
  # Never reset, overwrite or repair an existing SDK implicitly.
  if [[ ! -e "$TAKEOVER_IDF_PATH" ]]; then
    mapfile -t Pin < <(python3 - "$ToolDir/../Toolchain.lock.json" <<'PY'
import json, sys
sdk = json.load(open(sys.argv[1]))['sdk']
print(sdk['tag'])
print(sdk['repository'])
PY
)
    git clone --branch "${Pin[0]}" --recursive "${Pin[1]}" "$TAKEOVER_IDF_PATH"
  fi
  python3 "$ToolDir/VerifyToolchain.py" --sdk-only
  mkdir -p "$ToolDir/../generated"
  umask 077
  bash "$TAKEOVER_IDF_PATH/install.sh" esp32,esp32c3 >"$ToolDir/../generated/ToolchainInstall.log" 2>&1 || {
    echo 'SDK tool installation failed; inspect generated/ToolchainInstall.log.' >&2; exit 1;
  }
fi
python3 "$ToolDir/VerifyToolchain.py"
mkdir -p "$ToolDir/../generated"
umask 077
source "$TAKEOVER_IDF_PATH/export.sh" >"$ToolDir/../generated/ToolchainEnvironment.log" 2>&1
[[ "$(idf.py --version)" == 'ESP-IDF v5.5.1' ]] || { echo 'ESP-IDF 5.5.1 Python environment required.' >&2; exit 1; }
printf 'SDK Python environment verified. No device request.\n'
