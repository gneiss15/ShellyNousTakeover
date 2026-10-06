#!/usr/bin/env python3
# PackageShelly.py, Version: 1.00
"""Create the supported manufacturer app + blank-fs package, never raw flash parts."""
from pathlib import Path
import hashlib,json,zipfile
from VerifyBuild import verify_image
root=Path(__file__).resolve().parent.parent
out=root/'generated/ShellyTakeover/App'
image=(out/'Takeover.bin').read_bytes()
verify_image(out/'Takeover.bin',5,0x2a0000,'1.00')
assert image[80:112].split(b'\0')[0]==b'ShellyTakeover'
fs=b'\xff'*0xe0000
parts={}
for key,name,data in [('app','ShellyTakeover.bin',image),('fs','fs.img',fs)]:
    parts[key]={'type':key,'src':name,'size':len(data),'cs_sha256':hashlib.sha256(data).hexdigest(),'encrypt':True,'ptn':key+'_0'}
parts['fs']['fs_size']=len(fs)
import datetime
now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
manifest={'name':'PlugMG3','platform':'esp32c3','version':'99.0.0',
          'build_id':now.strftime('%Y%m%d-%H%M%S')+'/shelly-takeover-1.00',
          'build_timestamp':now.isoformat().replace('+00:00','Z'),'parts':parts}
for name in ['CandidateLoader','Rescue','OldTable','NewTable']:
    assert (out/(name+'.bin')).read_bytes() in image, 'Missing embedded payload: '+name
config=(out/'sdkconfig').read_text()
assert 'CONFIG_PARTITION_TABLE_OFFSET=0x10000\n' in config
for name in ['CONFIG_ESP_WIFI_NVS_ENABLED=y','CONFIG_ESP_PHY_CALIBRATION_AND_DATA_STORAGE=y']:
    assert name not in config
with zipfile.ZipFile(out/'PlugMG3-ShellyTakeover.zip','w',zipfile.ZIP_STORED) as archive:
    archive.writestr('manifest.json',json.dumps(manifest))
    archive.writestr('ShellyTakeover.bin',image)
    archive.writestr('fs.img',fs)
with zipfile.ZipFile(out/'PlugMG3-ShellyTakeover.zip') as archive:
    assert archive.testzip() is None
print('Manufacturer package created: app and blank fs only; no loader/partition-table OTA part.')
