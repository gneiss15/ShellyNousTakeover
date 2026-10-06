#!/usr/bin/env python3
# ValidateTakeoverPackage.py, Version: 1.01
"""Validate the current app + blank filesystem package before any manufacturer upload."""
from pathlib import Path
import hashlib,json,zipfile,os,re
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'generated/ShellyTakeover/App'


def validate(package):
    with zipfile.ZipFile(package) as archive:
        members=archive.namelist()
        if len(members)!=3 or set(members)!={'manifest.json','ShellyTakeover.bin','fs.img'} or archive.testzip():
            raise ValueError('Unexpected OTA members/CRC')
        manifest=json.loads(archive.read('manifest.json'))
        app=archive.read('ShellyTakeover.bin');fs=archive.read('fs.img')
        expected_type=os.environ.get('TAKEOVER_DEVICE_TYPE',(ROOT/'ShellyTakeover/DeviceType.txt').read_text().strip())
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]{0,30}',expected_type):raise ValueError('Invalid TAKEOVER_DEVICE_TYPE')
        rescue_dir=ROOT/'generated/ShellyTakeover/Rescue'
        rescue=(rescue_dir/'Rescue.bin').read_bytes()
        if (rescue_dir/'DeviceType.txt').read_text().strip()!=expected_type or rescue!=(OUT/'Rescue.bin').read_bytes() or rescue not in app:
            raise ValueError('Embedded Rescue differs from selected DeviceType/build; rebuild Takeover before upload')
        if app!=(OUT/'Takeover.bin').read_bytes() or fs!=b'\xff'*0xe0000:
            raise ValueError('Application differs from build or filesystem is not blank')
        if (manifest.get('name'),manifest.get('platform'),manifest.get('version'))!=('PlugMG3','esp32c3','99.0.0'):
            raise ValueError('Unexpected target/manifest version')
        parts=manifest.get('parts',{})
        if set(parts)!={'app','fs'}:
            raise ValueError('Unexpected OTA parts: loader/partition-table writes are forbidden here')
        for key,name,data in [('app','ShellyTakeover.bin',app),('fs','fs.img',fs)]:
            part=parts[key]
            if (part.get('type'),part.get('src'),part.get('ptn'),part.get('encrypt'))!=(key,name,key+'_0',True):
                raise ValueError('Unexpected manufacturer routing')
            if part.get('size')!=len(data) or part.get('cs_sha256')!=hashlib.sha256(data).hexdigest():
                raise ValueError('Part digest/size mismatch')
        if parts['fs'].get('fs_size')!=len(fs):
            raise ValueError('Wrong filesystem span')
    return len(app)


if __name__=='__main__':
    print('Takeover package validated; app bytes:',validate(OUT/'PlugMG3-ShellyTakeover.zip'))
