#!/usr/bin/env bash
# BuildRescue.sh, Version: 1.03
set -Eeuo pipefail
export GENERATED_TOOLS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
[[ ( $# == 1 && ( "$1" == shelly || "$1" == nous ) ) || ( $# == 2 && "$1" == shelly && "$2" == large ) ]] || {
  echo "Usage: $0 shelly [large] | nous" >&2; exit 2;
}
ToolDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$ToolDir/../common/Environment.sh"
Target=ShellyTakeover
Chip=esp32c3
[[ "$1" != nous ]] || { Target=NousTakeover; Chip=esp32; }
Generated="$TakeoverRoot/generated/$Target/Rescue"
Project="$TakeoverRoot/$Target/Rescue"
Layout="${2:-standard}"
if [[ "$Layout" == large ]]; then Generated="$TakeoverRoot/generated/$Target/RescueLarge"; fi
umask 077
mkdir -p "$Generated"
python3 "$ToolDir/PreparePrivate.py" "$Target" "$Generated"
DeviceType="${TAKEOVER_DEVICE_TYPE-$(cat "$TakeoverRoot/$Target/DeviceType.txt")}"
[[ "$DeviceType" =~ ^[A-Za-z][A-Za-z0-9]{0,30}$ ]] || { echo 'Invalid TAKEOVER_DEVICE_TYPE.' >&2; exit 2; }
python3 - "$ToolDir" "$DeviceType" "$Generated/DeviceType.input.txt" <<'PYTYPE'
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from BuildFiles import write_text_if_changed
write_text_if_changed(Path(sys.argv[3]),sys.argv[2]+'\n')
PYTYPE
python3 "$ToolDir/DeviceTypeArtifacts.py" prepare "$Generated/DeviceType.input.txt" "$Generated/DeviceType.inc.h" "$Generated/DeviceType.txt"
python3 "$ToolDir/DeviceTypeArtifacts.py" public-key-header "$TakeoverPrivate/public.key" "$Generated/EspUpdatePublicKey.h"
BuildOptions=()
if [[ "$Layout" == large ]]; then
  python3 - "$Project" "$Generated" <<'PYLAYOUT'
import csv
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, os.environ['GENERATED_TOOLS'])
from BuildFiles import write_text_if_changed

project, out = map(Path, sys.argv[1:])
table = project.parent / 'PartitionsLarge.csv'
with table.open() as partitions:
    entries = {
        label: (offset, size)
        for label, _, _, offset, size, _ in csv.reader(
            line for line in partitions if not line.startswith('#'))
    }
platform = (project / 'Platform.h').read_text()
for name, label in [('RESCUE', 'safeboot'), ('MAIN', 'app0'), ('FS', 'spiffs')]:
    for field, value in zip(('OFFSET', 'SIZE'), entries[label]):
        platform, count = re.subn(rf'(?m)^#define RESCUE_{name}_{field} \S+$',
                                  f'#define RESCUE_{name}_{field} {value}', platform)
        assert count == 1
write_text_if_changed(out / 'Platform.h', platform)
defaults = (project / 'sdkconfig.defaults').read_text()
defaults = defaults.replace('../partitions.csv', '../PartitionsLarge.csv')
write_text_if_changed(out / 'sdkconfig.defaults', defaults)
PYLAYOUT
  BuildOptions+=(-D "SDKCONFIG_DEFAULTS=$Generated/sdkconfig.defaults")
else
  python3 "$ToolDir/BuildFiles.py" "$Project/Platform.h" "$Generated/Platform.h"
fi
export TAKEOVER_RESCUE_GENERATED="$Generated"
python3 - "$Project/Platform.h" "$Generated/EspRescueHardware.h" <<'PY'
import sys as _generated_sys
import os as _generated_os
_generated_sys.path.insert(0, _generated_os.environ['GENERATED_TOOLS'])
from BuildFiles import write_text_if_changed, write_bytes_if_changed
from pathlib import Path
import sys
write_text_if_changed(Path(sys.argv[2]), '''#pragma once
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
IDF_TARGET="$Chip" idf.py -C "$Project" -B "$Generated/build" -D "SDKCONFIG=$Generated/sdkconfig" "${BuildOptions[@]}" build >"$Generated/Build.log" 2>&1 || {
  echo "Rescue build failed; inspect local generated/$Target/Rescue/Build.log" >&2; exit 1;
}
cp "$Generated/build/${Target}Rescue.bin" "$Generated/Rescue.bin"
if [[ "$Layout" == large && "$(wc -c <"$Generated/Rescue.bin")" -gt $((0xC0000)) ]]; then
  echo 'Rescue image exceeds the large-layout Rescue partition.' >&2
  exit 1
fi
python3 "$ToolDir/DeviceTypeArtifacts.py" wrap "$Generated/DeviceType.txt" rescue "$Generated/Rescue.bin" "$Generated/Rescue.unsigned"
python3 "$ToolDir/DeviceTypeArtifacts.py" sign "$Generated/Rescue.unsigned" "$TakeoverPrivate/private.key" "$Generated/Rescue.signed"
python3 "$ToolDir/DeviceTypeArtifacts.py" verify "$Generated/Rescue.signed" "$TakeoverPrivate/public.key"
rm "$Generated/Rescue.unsigned"
printf '%s Rescue built and signed. No upload.\n' "$Target"
