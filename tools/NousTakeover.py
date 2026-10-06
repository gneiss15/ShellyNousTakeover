#!/usr/bin/env python3
# NousTakeover.py, Version: 1.01
"""Read-only preflight by default; explicit manufacturer upload and Rescue verification."""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parent.parent
class TakeoverError(Exception):
    pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None
class Http:
    def __init__(self,ip):
        self.base='http://'+str(ipaddress.IPv4Address(ip))
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        self.auth=None
        if os.environ.get('NOUS_PASSWORD'):
            value=os.environ.get('NOUS_USER','admin')+':'+os.environ['NOUS_PASSWORD']
            self.auth='Basic '+base64.b64encode(value.encode()).decode()
    def request(self,path,data=None,headers=None,timeout=10,manufacturer=True):
        request=urllib.request.Request(self.base+path,data=data,headers=headers or {})
        if manufacturer and self.auth:request.add_header('Authorization',self.auth)
        with self.opener.open(request,timeout=timeout) as response:
            raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:raise TakeoverError('Oversized device response')
            return raw
    def command(self,text):
        raw=self.request('/cm?'+urllib.parse.urlencode({'cmnd':text}))
        value=json.loads(raw)
        if not isinstance(value,dict):raise TakeoverError('Invalid Tasmota response')
        return value

def mac(value):
    if not isinstance(value,str):raise TakeoverError('Missing device MAC')
    normalized=value.replace(':','').replace('-','').upper()
    if not re.fullmatch(r'[0-9A-F]{12}',normalized):raise TakeoverError('Invalid device MAC')
    return normalized

def preflight(http):
    fw=http.command('Status 2').get('StatusFWR',{})
    identity=json.loads((ROOT/'NousTakeover/OriginalFirmware.json').read_text())['observed_tasmota']
    if fw.get('Version')!=identity['version']+'('+identity['variant']+')' or fw.get('BuildDateTime')!=identity['build']:
        raise TakeoverError('Unsupported original Tasmota version/build; no upload')
    if not str(fw.get('Hardware','')).startswith('ESP32-D0WD'):
        raise TakeoverError('Unsupported Tasmota hardware; no upload')
    memory=http.command('Status 4').get('StatusMEM',{})
    if memory.get('FlashSize')!=4096:raise TakeoverError('Expected 4 MiB flash; no upload')
    template=http.command('Template')
    if isinstance(template.get('Template'),dict):template=template['Template']
    expected=[1,1,576,1,32,1,1,1,1,224,2624,1,1,1,1,1,0,1,1,1,0,1,2656,2720,0,0,0,0,1,1,1,1,1,0,0,1]
    gpio=template.get('GPIO')
    if not isinstance(gpio,list) or len(gpio)!=len(expected):raise TakeoverError('Missing NOUS A8T template; no upload')
    # Led_i and LinkLed_i use the same inverse LED pin; other assignments must match.
    if gpio[2] not in (320,576) or gpio[:2]+[576]+gpio[3:]!=expected or template.get('BASE')!=1 or template.get('FLAG')!=0:
        raise TakeoverError('Unexpected NOUS A8T GPIO template; no upload')
    if str(template.get('NAME','')).replace(' ','').upper()!='NOUSA8T':raise TakeoverError('Wrong model template; no upload')
    module=http.command('Module').get('Module',{})
    if not isinstance(module,dict) or list(module)!=['0']:raise TakeoverError('NOUS template is not the active module; no upload')
    network=http.command('Status 5').get('StatusNET',{})
    if network.get('IPAddress')!=http.base.removeprefix('http://'):raise TakeoverError('Use the station/LAN address; no upload')
    device_mac=mac(network.get('Mac'))
    page=http.request('/up')
    if b'u2?fsz=' not in page or b'name=\'u2\'' not in page and b'name="u2"' not in page:
        raise TakeoverError('Tasmota file-upload form missing; no upload')
    # Empty selector only reports single-OTA availability; it cannot request a restart.
    if http.request('/u4?api=1').strip()!=b'true':raise TakeoverError('Tasmota SafeBoot layout is unavailable; no upload')
    return device_mac

def rescue_verified(status,expected_mac,target='nous'):
    if not isinstance(status,dict) or status.get('Application')!='Rescue':return False
    project,offset={'nous':('NousTakeover',0x10000),'shelly':('ShellyTakeover',0x640000)}[target]
    device_type=os.environ.get('TAKEOVER_DEVICE_TYPE',(ROOT/project/'DeviceType.txt').read_text().strip())
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]{0,30}',device_type):raise TakeoverError('Invalid TAKEOVER_DEVICE_TYPE')
    if status.get('Project')!=project or status.get('DeviceType')!=device_type or status.get('Version')!='1.00':
        raise TakeoverError('Different Rescue identity/version at target IP')
    if mac(status.get('Mac'))!=expected_mac:raise TakeoverError('Different device MAC after migration')
    if status.get('GeometryValid') is not True or status.get('RunningOffset')!=offset or status.get('BootOffset')!=offset or status.get('MainReady') is not False:
        raise TakeoverError('Rescue geometry/boot/Main-empty verification failed')
    return True

def wait_rescue(http,expected_mac,timeout=240,clock=time.monotonic,sleep=time.sleep,target='nous'):
    deadline=clock()+timeout;last_phase=None
    while clock()<deadline:
        try:
            status=json.loads(http.request('/status',manufacturer=False))
        except (urllib.error.URLError,TimeoutError,OSError,json.JSONDecodeError):
            sleep(2);continue
        if rescue_verified(status,expected_mac,target):return
        if isinstance(status,dict) and status.get('Application')==('NousTakeover' if target=='nous' else 'ShellyTakeover'):
            if status.get('Phase')!=last_phase:
                last_phase=status.get('Phase');print('Takeover phase:',last_phase,flush=True)
            if last_phase=='Failed':
                raise TakeoverError('Takeover failed: '+str(status.get('Error',''))+'; RollbackVerified='+str(status.get('RollbackVerified'))+'; DoNotRestart='+str(status.get('DoNotRestart')))
        sleep(2)
    raise TakeoverError('Rescue not verified within deadline; no retry upload or automatic reset. Inspect device diagnosis.')

def execute(http,expected_mac,image,sleep=time.sleep,clock=time.monotonic):
    # Validate before requesting any restart or upload.
    subprocess.run([sys.executable,str(ROOT/'tools/ValidateNousTakeover.py'),str(image)],check=True)
    data=image.read_bytes()
    # Verify that all read-only manufacturer prerequisites still match immediately before restart.
    if preflight(http)!=expected_mac:raise TakeoverError('Device identity changed; no upload')
    answer=http.request('/u4?u4=fct&api=1').strip()
    if answer not in (b'true',b'false'):raise TakeoverError('SafeBoot switch rejected; no upload')
    deadline=clock()+90
    while clock()<deadline:
        try:
            page=http.request('/')
            if re.search(rb'<h3>\s*SafeBoot\s*</h3>',page,re.I):break
        except (urllib.error.URLError,TimeoutError,OSError):pass
        sleep(2)
    else:raise TakeoverError('SafeBoot startup not confirmed; no upload')
    # A successful page fetch alone is insufficient: retain the same station identity.
    if mac(http.command('Status 5').get('StatusNET',{}).get('Mac'))!=expected_mac:
        raise TakeoverError('SafeBoot device identity changed; no upload')
    if http.request('/u4?api=1').strip()!=b'true':raise TakeoverError('SafeBoot layout changed; no upload')
    if b'u2?fsz=' not in http.request('/up'):raise TakeoverError('SafeBoot upload route unavailable')
    boundary='Takeover'+uuid.uuid4().hex
    body=('--'+boundary+'\r\nContent-Disposition: form-data; name="u2"; filename="NousTakeover.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode()
    print('Sending manufacturer image once; waiting for verified Rescue.',flush=True)
    try:
        http.request('/u2?fsz='+str(len(data)),data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary},timeout=120)
    except (urllib.error.URLError,TimeoutError,OSError):
        # The reply can disappear during restart; never repeat an uncertain upload.
        print('Upload response unavailable; checking status without another write.',flush=True)
    wait_rescue(http,expected_mac)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='switch to SafeBoot, upload once and verify Rescue')
    args=parser.parse_args()
    if not os.environ.get('NOUS_IP'):raise TakeoverError('Set NOUS_IP to the fixed station IPv4 address')
    http=Http(os.environ['NOUS_IP']);device_mac=preflight(http)
    print('NOUS/Tasmota/SafeBoot preflight passed; exact flash/layout/loader guards run inside Takeover.')
    if not args.execute:
        print('Read-only check completed; no restart or upload.');return
    execute(http,device_mac,ROOT/'generated/NousTakeover/App/Takeover.bin')
    print('Same device verified in Rescue; Main is not installed. Migration completed.')
if __name__=='__main__':
    try:main()
    except (TakeoverError,ValueError,KeyError,AssertionError,urllib.error.URLError,OSError,subprocess.CalledProcessError):
        # Do not print request objects, headers, private values or complete device replies.
        error=sys.exc_info()[1]
        print(str(error) if isinstance(error,TakeoverError) else 'Device/build check failed; no automatic retry or reset.',file=sys.stderr)
        raise SystemExit(1)
