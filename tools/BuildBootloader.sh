#!/usr/bin/env bash
# BuildBootloader.sh, Version: 1.01
set -Eeuo pipefail
[[ $# == 1 && ( "$1" == shelly || "$1" == nous ) ]] || { echo "Usage: $0 shelly|nous" >&2; exit 2; }
ToolDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
: "${TAKEOVER_IDF_PATH:?Set TAKEOVER_IDF_PATH}"
: "${TAKEOVER_IDF_TOOLS_PATH:?Set TAKEOVER_IDF_TOOLS_PATH}"
export IDF_TOOLS_PATH="$TAKEOVER_IDF_TOOLS_PATH"
Root="$(cd -- "$ToolDir/.." && pwd -P)"
Target=ShellyTakeover
Chip=esp32c3
[[ "$1" != nous ]] || { Target=NousTakeover; Chip=esp32; }
Generated="$Root/generated/$Target/Bootloader"
mkdir -p "$Generated"
python3 "$ToolDir/VerifyToolchain.py" --target "$1"
source "$TAKEOVER_IDF_PATH/export.sh" >"$Generated/Environment.log" 2>&1
[[ "$(idf.py --version)" == 'ESP-IDF v5.5.1' ]] || { echo 'ESP-IDF 5.5.1 required.' >&2; exit 1; }
export PATH="$IDF_TOOLS_PATH/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin:$IDF_TOOLS_PATH/tools/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin:$PATH"
if [[ "$1" == shelly ]]; then
  python3 - "$Root" "$Generated" <<'PY'
from pathlib import Path
import os, subprocess, sys
root, out = map(Path, sys.argv[1:])
generator = Path(os.environ['IDF_PATH'])/'components/partition_table/gen_esp32part.py'
text = '// Generated exact partition-table fixtures.\n'
for name, csv in [('StockTable','StockPartitions.csv'),('RescueTable','partitions.csv')]:
    binary = out/(name+'.bin')
    subprocess.run([sys.executable,str(generator),'--offset','0x10000',str(root/'ShellyTakeover'/csv),str(binary)],check=True)
    data=binary.read_bytes(); end=data.index(b'\xeb\xeb')+32
    assert all(v==255 for v in data[end:])
    text+='static const unsigned char '+name+'[] = {'+','.join(str(v) for v in data[:end])+'};\n'
(out/'ExpectedTables.h').write_text(text)
PY
fi
IDF_TARGET="$Chip" idf.py -C "$Root/$Target/Bootloader" -B "$Generated/build" -D "SDKCONFIG=$Generated/sdkconfig" bootloader >"$Generated/Build.log" 2>&1 || {
  echo "Bootloader build failed; inspect generated/$Target/Bootloader/Build.log" >&2; exit 1;
}
cp "$Generated/build/bootloader/bootloader.bin" "$Generated/Bootloader.bin"
python3 - "$Generated/Bootloader.bin" "$1" <<'PY'
from pathlib import Path
import sys
image=Path(sys.argv[1]).read_bytes(); limit=0x6000 if sys.argv[2]=='shelly' else 0x7000
assert image[0]==0xe9 and 0<len(image)<=limit
print('Bootloader size checked:',len(image),'/',limit,'bytes; no upload.')
PY
