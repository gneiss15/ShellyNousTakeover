#!/usr/bin/env bash
# BuildTakeover.sh, Version: 1.01
set -Eeuo pipefail
[[ $# == 1 && ( "$1" == shelly || "$1" == nous ) ]] || { echo "Usage: $0 shelly|nous" >&2; exit 2; }
ToolDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$ToolDir/../common/Environment.sh"
bash "$ToolDir/BuildBootloader.sh" "$1"
bash "$ToolDir/BuildRescue.sh" "$1"
if [[ "$1" == shelly ]]; then Target=ShellyTakeover; Chip=esp32c3; else Target=NousTakeover; Chip=esp32; fi
Generated="$TakeoverRoot/generated/$Target/App"
umask 077
mkdir -p "$Generated"
python3 "$ToolDir/PreparePrivate.py" "$Target" "$Generated"
python3 - "$TakeoverRoot" "$Generated" "$Target" <<'PY'
from pathlib import Path
import hashlib,json,os,subprocess,sys
root,out=map(Path,sys.argv[1:3]);target=sys.argv[3];built=root/'generated'/target
span=0x6000 if target=='ShellyTakeover' else 0x7000
loader=(built/'Bootloader/Bootloader.bin').read_bytes();assert len(loader)<=span
loader=loader.ljust(span,b'\xff');(out/'CandidateLoader.bin').write_bytes(loader)
rescue=(built/'Rescue/Rescue.bin').read_bytes();assert len(rescue)<=(0x180000 if target=='ShellyTakeover' else 0xD0000)
(out/'Rescue.bin').write_bytes(rescue)
if target=='ShellyTakeover':
 for name in ['OldTable','NewTable']:
  table=(built/'Bootloader'/('StockTable.bin' if name=='OldTable' else 'RescueTable.bin')).read_bytes()
  (out/(name+'.bin')).write_bytes(table.ljust(4096,b'\xff'))
else:
 generator=Path(os.environ['TAKEOVER_IDF_PATH'])/'components/partition_table/gen_esp32part.py'
 subprocess.run([sys.executable,str(generator),'--offset','0x8000',str(root/target/'partitions.csv'),str(out/'ExpectedTable.bin')],check=True)
 table=(out/'ExpectedTable.bin').read_bytes().ljust(4096,b'\xff');(out/'ExpectedTable.bin').write_bytes(table)
 identity=json.loads((root/target/'OriginalFirmware.json').read_text())
 assert hashlib.sha256(table).hexdigest()==identity['partition_table']['span_sha256']
header='#pragma once\n#define TAKEOVER_RESCUE_SIZE '+str(len(rescue))+'u\n'
for name,data in [('Loader',loader),('Rescue',rescue)]:
 header+='static const unsigned char Takeover'+name+'Hash[32] = {'+','.join(str(v) for v in hashlib.sha256(data).digest())+'};\n'
if target=='NousTakeover':
 original=bytes.fromhex(identity['bootloader']['span_sha256']);assert len(original)==32
 header+='static const unsigned char TakeoverOriginalLoaderHash[32] = {'+','.join(str(v) for v in original)+'};\n'
(out/'PayloadIdentity.h').write_text(header)
PY
source "$TAKEOVER_IDF_PATH/export.sh" >"$Generated/Environment.log" 2>&1
export PATH="$IDF_TOOLS_PATH/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin:$IDF_TOOLS_PATH/tools/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin:$PATH"
IDF_TARGET="$Chip" idf.py -C "$TakeoverRoot/$Target/App" -B "$Generated/build" -D "SDKCONFIG=$Generated/sdkconfig" build >"$Generated/Build.log" 2>&1 || {
  echo "Takeover build failed; inspect generated/$Target/App/Build.log" >&2; exit 1;
}
cp "$Generated/build/$Target.bin" "$Generated/Takeover.bin"
if [[ "$1" == shelly ]]; then python3 "$ToolDir/PackageShelly.py"; else python3 "$ToolDir/ValidateNousTakeover.py"; fi
printf 'Automatic %s built; no upload.\n' "$Target"
