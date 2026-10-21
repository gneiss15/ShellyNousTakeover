#!/usr/bin/env bash
# BuildExample.sh, Version: 1.02
set -Eeuo pipefail
export GENERATED_TOOLS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
[[ $# == 1 && ( "$1" == shelly || "$1" == nous ) ]] || { echo "Usage: $0 shelly|nous" >&2; exit 2; }
ToolDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$ToolDir/../common/Environment.sh"
Target=ShellyTakeover
Chip=esp32c3
[[ "$1" != nous ]] || { Target=NousTakeover; Chip=esp32; }
export MINI_GENERATED="$TakeoverRoot/generated/$Target/MiniMain"
umask 077
mkdir -p "$MINI_GENERATED"
DeviceType="${TAKEOVER_DEVICE_TYPE-$(cat "$TakeoverRoot/$Target/DeviceType.txt")}"
[[ "$DeviceType" =~ ^[A-Za-z][A-Za-z0-9]{0,30}$ ]] || { echo 'Invalid TAKEOVER_DEVICE_TYPE.' >&2; exit 2; }
python3 - "$ToolDir" "$DeviceType" "$MINI_GENERATED/DeviceType.input.txt" <<'PYTYPE'
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from BuildFiles import write_text_if_changed
write_text_if_changed(Path(sys.argv[3]),sys.argv[2]+'\n')
PYTYPE
python3 "$ToolDir/DeviceTypeArtifacts.py" prepare "$MINI_GENERATED/DeviceType.input.txt" "$MINI_GENERATED/DeviceType.inc.h" "$MINI_GENERATED/DeviceType.txt"
python3 "$ToolDir/PreparePrivate.py" "$Target" "$MINI_GENERATED"
python3 "$ToolDir/BuildFiles.py" "$TakeoverRoot/$Target/Rescue/Platform.h" "$MINI_GENERATED/Platform.h"
python3 - "$TakeoverRoot" "$Target" "$MINI_GENERATED" <<'PY'
import sys as _generated_sys
import os as _generated_os
_generated_sys.path.insert(0, _generated_os.environ['GENERATED_TOOLS'])
from BuildFiles import write_text_if_changed, write_bytes_if_changed
from pathlib import Path
import sys
root=Path(sys.argv[1]);target=sys.argv[2];out=Path(sys.argv[3])
text=(root/target/'Rescue/sdkconfig.defaults').read_text()
text=text.replace('CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="../partitions.csv"',
                  'CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="'+str(root/target/'partitions.csv')+'"')
write_text_if_changed(out/'sdkconfig.defaults', text)
PY
python3 "$ToolDir/VerifyToolchain.py" --target "$1"
source "$TAKEOVER_IDF_PATH/export.sh" > "$MINI_GENERATED/Environment.log" 2>&1
export PATH="$IDF_TOOLS_PATH/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin:$IDF_TOOLS_PATH/tools/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin:$PATH"
IDF_TARGET="$Chip" idf.py -C "$TakeoverRoot/Examples/MiniMain" -B "$MINI_GENERATED/build" \
  -D "SDKCONFIG=$MINI_GENERATED/sdkconfig" -D "SDKCONFIG_DEFAULTS=$MINI_GENERATED/sdkconfig.defaults" build > "$MINI_GENERATED/Build.log" 2>&1 || {
  echo "Example build failed; inspect generated/$Target/MiniMain/Build.log" >&2; exit 1;
}
cp "$MINI_GENERATED/build/MiniMain.bin" "$MINI_GENERATED/MiniMain.bin"
python3 - "$ToolDir" "$MINI_GENERATED" "$Chip" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0,sys.argv[1])
from VerifyBuild import verify_image
out=Path(sys.argv[2]);shelly=sys.argv[3]=='esp32c3'
root=Path(sys.argv[1]).parent
versions={key:value for key,value in (line.strip().split('=',1) for line in (root/'Versions.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#'))}
verify_image(out/'MiniMain.bin',5 if shelly else 0,0x2a0000 if shelly else 0x2d0000,versions['MiniMain'])
assert (out/'MiniMain.bin').read_bytes()[80:112].split(b'\0')[0]==b'MiniMain'
config=(out/'sdkconfig').read_text()
assert 'CONFIG_PARTITION_TABLE_OFFSET='+('0x10000' if shelly else '0x8000')+'\n' in config
assert 'CONFIG_ESP_WIFI_NVS_ENABLED=y' not in config
assert 'CONFIG_ESP_PHY_CALIBRATION_AND_DATA_STORAGE=y' not in config
print('Example image/descriptor/chip/SDK geometry verified; no hardware test.')
PY
python3 "$ToolDir/DeviceTypeArtifacts.py" wrap "$MINI_GENERATED/DeviceType.txt" firmware "$MINI_GENERATED/MiniMain.bin" "$MINI_GENERATED/MiniMain.unsigned"
python3 "$ToolDir/DeviceTypeArtifacts.py" sign "$MINI_GENERATED/MiniMain.unsigned" "$TakeoverPrivate/private.key" "$MINI_GENERATED/MiniMain.signed"
python3 "$ToolDir/DeviceTypeArtifacts.py" verify "$MINI_GENERATED/MiniMain.signed" "$TakeoverPrivate/public.key"
rm "$MINI_GENERATED/MiniMain.unsigned"
echo "$Target MiniMain built and signed. No upload."
