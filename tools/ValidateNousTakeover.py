#!/usr/bin/env python3
# ValidateNousTakeover.py, Version: 1.01
"""Validate manufacturer-upload image and embedded payloads; never contact a device."""
from pathlib import Path
import sys
from VerifyBuild import verify_image

root=Path(__file__).resolve().parent.parent
directory=root/'generated/NousTakeover/App'
path=Path(sys.argv[1]) if len(sys.argv)==2 else directory/'Takeover.bin'
if len(sys.argv)>2:
    raise SystemExit('Usage: ValidateNousTakeover.py [image.bin]')
versions={key:value for key,value in (line.strip().split('=',1) for line in (root/'Versions.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#'))}
size=verify_image(path,0,0x2D0000,versions['NousApp'])
data=path.read_bytes()
assert data[80:112].split(b'\0')[0]==b'NousTakeover', 'Wrong application project'
for name in ['CandidateLoader.bin','Rescue.bin','ExpectedTable.bin']:
    payload=(directory/name).read_bytes()
    assert payload and payload in data, 'Missing or different embedded '+name
config=(directory/'sdkconfig').read_text()
for setting in ['CONFIG_PARTITION_TABLE_OFFSET=0x8000','CONFIG_ESPTOOLPY_FLASHSIZE_4MB=y']:
    assert setting+'\n' in config, 'Wrong SDK geometry'
assert 'CONFIG_ESP_WIFI_NVS_ENABLED=y' not in config, 'WiFi NVS must remain disabled'
assert 'CONFIG_ESP_PHY_CALIBRATION_AND_DATA_STORAGE=y' not in config, 'PHY persistence must remain disabled'
print('Nous manufacturer-upload image checked:',size,'bytes; ESP32, checksum, descriptor, embedded payloads and SDK geometry. No upload.')
