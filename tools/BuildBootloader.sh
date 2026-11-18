#!/usr/bin/env bash
# BuildBootloader.sh, Version: 1.04
set -Eeuo pipefail
export GENERATED_TOOLS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
[[ ( $# == 1 && ( "$1" == shelly || "$1" == nous ) ) || ( $# == 2 && "$1" == shelly && "$2" == large ) ]] || {
  echo "Usage: $0 shelly [large] | nous" >&2; exit 2;
}
ToolDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
: "${TAKEOVER_IDF_PATH:?Set TAKEOVER_IDF_PATH}"
: "${TAKEOVER_IDF_TOOLS_PATH:?Set TAKEOVER_IDF_TOOLS_PATH}"
export IDF_TOOLS_PATH="$TAKEOVER_IDF_TOOLS_PATH"
Root="$(cd -- "$ToolDir/.." && pwd -P)"
Target=ShellyTakeover
Chip=esp32c3
[[ "$1" != nous ]] || { Target=NousTakeover; Chip=esp32; }
Generated="$Root/generated/$Target/Bootloader"
Layout="${2:-standard}"
if [[ "$Layout" == large ]]; then Generated="$Root/generated/$Target/BootloaderLarge"; fi
export TAKEOVER_BOOTLOADER_GENERATED="$Generated"
mkdir -p "$Generated"
python3 "$ToolDir/VerifyToolchain.py" --target "$1"
source "$TAKEOVER_IDF_PATH/export.sh" >"$Generated/Environment.log" 2>&1
[[ "$(idf.py --version)" == 'ESP-IDF v5.5.1' ]] || { echo 'ESP-IDF 5.5.1 required.' >&2; exit 1; }
export PATH="$IDF_TOOLS_PATH/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin:$IDF_TOOLS_PATH/tools/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin:$PATH"
if [[ "$1" == shelly ]]; then
  python3 - "$Root" "$Generated" "$Layout" <<'PY'
import sys as _generated_sys
import os as _generated_os
_generated_sys.path.insert(0, _generated_os.environ['GENERATED_TOOLS'])
from BuildFiles import write_text_if_changed, write_bytes_if_changed, generate_output_if_changed
from pathlib import Path
import hashlib, os, struct, sys
root, out = map(Path, sys.argv[1:3])
large = sys.argv[3] == 'large'
generator = Path(os.environ['IDF_PATH'])/'components/partition_table/gen_esp32part.py'
text = '// Generated exact partition-table fixtures.\n'
stock_csv = 'StockPartitionsLarge.csv' if large else 'StockPartitions.csv'
rescue_csv = 'PartitionsLarge.csv' if large else 'partitions.csv'
entries = {}
for name, csv in [('StockTable',stock_csv),('RescueTable',rescue_csv)]:
    binary = out/(name+'.bin')
    replicated = large and name == 'StockTable'
    idf_binary = out/'StockTablePrimary.bin' if replicated else binary
    generate_output_if_changed([sys.executable,str(generator),'--offset','0x10000',str(root/'ShellyTakeover'/csv),str(idf_binary)], padding=0)
    data=idf_binary.read_bytes()
    end=data.index(b'\xeb\xeb')+32
    assert all(v==255 for v in data[end:])
    if replicated:
        # The complete supplier sector repeats the same table four times.
        assert end <= 1024
        sector = data[:end].ljust(1024, b'\xff') * 4
        assert hashlib.sha256(sector).hexdigest() == 'e5bdb5e4268dd3b656f16be686dc33aa459119932d8fe3a5e89c5f302e826eb0'
        write_bytes_if_changed(binary, sector)
        text += '#define STOCK_TABLE_COPIES 4\n'
    entries[name] = {
        label.rstrip(b'\0').decode(): (offset, size)
        for _, _, _, offset, size, label, _ in struct.iter_unpack('<HBBII16sI', data[:end-32])
    }
    text+='static const unsigned char '+name+'[] = {'+','.join(str(v) for v in data[:end])+'};\n'
stock, rescue = entries['StockTable'], entries['RescueTable']
assert stock['app_0'][0] == 0x20000 and stock['otadata'] == (0x11000, 0x2000)
assert stock['app_1'] == rescue['app0'] and rescue['otadata'][1] == 0x2000
for original, target in [
    ('app_0', 'stock_app'), ('fs_0', 'spiffs'), ('nvs', 'stock_nvs'),
    ('otadata', 'stockboot'), ('shelly', 'shelly'),
]:
    assert stock[original] == rescue[target]
assert rescue['safeboot'][0] == stock['fs_1'][0]
checkpoint = (rescue['otadata'][0] + rescue['otadata'][1], 0x8000)
protected = [stock[key] for key in ('app_0', 'fs_0', 'nvs', 'app_1', 'shelly')]
writes = [rescue[key] for key in ('safeboot', 'nvs', 'otadata')] + [checkpoint]
for start, size in writes:
    assert all(start + size <= pos or pos + span <= start for pos, span in protected)
    assert start + size <= 0x800000
for name, value in {
    'APP0_SIZE': stock['app_0'][1],
    'APP1_OFFSET': stock['app_1'][0],
    'APP1_SIZE': stock['app_1'][1],
    'RESCUE_OFFSET': rescue['safeboot'][0],
    'RESCUE_SIZE': rescue['safeboot'][1],
    'OTA_OFFSET': rescue['otadata'][0],
}.items():
    text += f'#define {name} {value:#x}\n'
write_text_if_changed(out/'ExpectedTables.h', text)
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
