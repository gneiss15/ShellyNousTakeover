#!/usr/bin/env bash
# CheckEnvironment.sh, Version: 1.03
set -Eeuo pipefail
[[ $# == 1 && ( "$1" == shelly || "$1" == nous ) ]] || {
  echo "Usage: bash $0 shelly|nous" >&2; exit 2;
}
ToolDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
[[ "$(uname -s)" == Linux ]] || { echo 'Linux is required.' >&2; exit 1; }
for Tool in bash python3 git cmake ninja openssl; do
  command -v "$Tool" >/dev/null || { echo "Missing tool: $Tool" >&2; exit 1; }
done
source "$ToolDir/../common/Environment.sh"
python3 - "$1" <<'PY'
import ipaddress
import os
import sys
name = 'SHELLY_IP' if sys.argv[1] == 'shelly' else 'NOUS_IP'
try:
    address = ipaddress.IPv4Address(os.environ.get(name, ''))
except ipaddress.AddressValueError:
    raise SystemExit('Set ' + name + ' to the target LAN IPv4 address, without URL/port.')
if address.is_unspecified or address.is_multicast or address.is_loopback or address == ipaddress.IPv4Address('255.255.255.255'):
    raise SystemExit(name + ' is not a usable target address.')
print(name + ': format checked; device identity/network reachability not yet checked.')
PY
# Source only the explicitly selected SDK; keep potentially noisy activation local.
mkdir -p "$ToolDir/../generated"
umask 077
python3 "$ToolDir/VerifyToolchain.py" --target "$1"
source "$TAKEOVER_IDF_PATH/export.sh" >"$ToolDir/../generated/Environment.log" 2>&1
export PATH="$IDF_TOOLS_PATH/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin:$IDF_TOOLS_PATH/tools/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin:$PATH"
[[ "$(idf.py --version)" == 'ESP-IDF v5.5.1' ]] || { echo 'ESP-IDF 5.5.1 required.' >&2; exit 1; }
Compiler=riscv32-esp-elf-gcc
[[ "$1" != nous ]] || Compiler=xtensa-esp32-elf-gcc
command -v "$Compiler" >/dev/null || { echo "Compiler missing from activated SDK: $Compiler" >&2; exit 1; }

idf.py --version
"$Compiler" --version | head -n 1
printf 'Environment checked. No build, download or device request performed.\n'
