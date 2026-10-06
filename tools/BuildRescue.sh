#!/usr/bin/env bash
# BuildRescue.sh, Version: 1.02
set -Eeuo pipefail
[[ $# == 1 && ( "$1" == shelly || "$1" == nous ) ]] || { echo "Usage: $0 shelly|nous" >&2; exit 2; }
ToolDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$ToolDir/../common/Environment.sh"
Target=ShellyTakeover
Chip=esp32c3
[[ "$1" != nous ]] || { Target=NousTakeover; Chip=esp32; }
Generated="$TakeoverRoot/generated/$Target/Rescue"
Project="$TakeoverRoot/$Target/Rescue"
umask 077
mkdir -p "$Generated"
python3 "$ToolDir/PreparePrivate.py" "$Target" "$Generated"
DeviceType="${TAKEOVER_DEVICE_TYPE-$(cat "$TakeoverRoot/$Target/DeviceType.txt")}"
[[ "$DeviceType" =~ ^[A-Za-z][A-Za-z0-9]{0,30}$ ]] || { echo 'Invalid TAKEOVER_DEVICE_TYPE.' >&2; exit 2; }
printf '%s\n' "$DeviceType" > "$Generated/DeviceType.input.txt"
python3 "$ToolDir/DeviceTypeArtifacts.py" prepare "$Generated/DeviceType.input.txt" "$Generated/DeviceType.inc.h" "$Generated/DeviceType.txt"
python3 "$ToolDir/DeviceTypeArtifacts.py" public-key-header "$TakeoverPrivate/public.key" "$Generated/EspUpdatePublicKey.h"
cp "$Project/Platform.h" "$Generated/Platform.h"
python3 - "$Project/Platform.h" "$Generated/EspRescueHardware.h" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[2]).write_text('''#pragma once
#include "Platform.h"
namespace EspRescueHardware
 {
constexpr int KeyPin = RESCUE_KEY_PIN;
constexpr int KeyActiveLevel = LOW;
constexpr int StatusLedPin = RESCUE_LED_PIN;
constexpr int StatusLedActiveLevel = LOW;
 }
''')
PY
python3 "$ToolDir/VerifyToolchain.py" --target "$1"
source "$TAKEOVER_IDF_PATH/export.sh" >"$Generated/Environment.log" 2>&1
[[ "$(idf.py --version)" == 'ESP-IDF v5.5.1' ]] || { echo 'ESP-IDF 5.5.1 required.' >&2; exit 1; }
# Both compilers use the tool installation selected by the user.
export PATH="$IDF_TOOLS_PATH/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin:$IDF_TOOLS_PATH/tools/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin:$PATH"
IDF_TARGET="$Chip" idf.py -C "$Project" -B "$Generated/build" -D "SDKCONFIG=$Generated/sdkconfig" build >"$Generated/Build.log" 2>&1 || {
  echo "Rescue build failed; inspect local generated/$Target/Rescue/Build.log" >&2; exit 1;
}
cp "$Generated/build/${Target}Rescue.bin" "$Generated/Rescue.bin"
python3 "$ToolDir/DeviceTypeArtifacts.py" wrap "$Generated/DeviceType.txt" rescue "$Generated/Rescue.bin" "$Generated/Rescue.unsigned"
python3 "$ToolDir/DeviceTypeArtifacts.py" sign "$Generated/Rescue.unsigned" "$TakeoverPrivate/private.key" "$Generated/Rescue.signed"
python3 "$ToolDir/DeviceTypeArtifacts.py" verify "$Generated/Rescue.signed" "$TakeoverPrivate/public.key"
rm "$Generated/Rescue.unsigned"
printf '%s Rescue built and signed. No upload.\n' "$Target"
