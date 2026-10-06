#!/usr/bin/env python3
# StockFirmware.py, Version: 1.03
"""Pinned stock package preparation and same-device update checks; no firmware guessing."""
import hashlib
import json
from pathlib import Path
import subprocess
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from NousTakeover import NoRedirect,TakeoverError

ROOT=Path(__file__).resolve().parent.parent
LAYOUT=ROOT/'ShellyTakeover/StockFirmware.layout.json'
POLICY=ROOT/'ShellyTakeover/StockUpdatePolicy.json'

def policy():
    value=json.loads(POLICY.read_text());layout=json.loads(LAYOUT.read_text())
    target=value['target'];url=urllib.parse.urlsplit(target['url'])
    if (value['model'],value['app'])!=(layout['model'],layout['name']) or target['version']!=layout['version'] or target['build_id']!=layout['build_id']:
        raise TakeoverError('Stock policy and package identity differ')
    if url.scheme!='https' or url.hostname!='fwcdn.shelly.cloud' or url.port not in (None,443) or url.username or url.password or url.query or url.fragment or Path(url.path).name!=layout['package_sha256']:
        raise TakeoverError('Pinned stock download URL is invalid')
    if value.get('downgrade_supported') is not False:raise TakeoverError('No checked downgrade policy is available')
    return value

def classify(public):
    value=policy()
    if public.get('model')!=value['model'] or public.get('app')!=value['app']:raise TakeoverError('Unsupported stock device model')
    actual=(public.get('ver'),public.get('fw_id'))
    accepted=[value['target']]+value.get('accepted_stock',[])
    if any(actual==(item['version'],item['build_id']) for item in accepted):return 'ready'
    if any(actual==(s['version'],s['build_id']) for s in value['allowed_sources']):return 'update_available'
    raise TakeoverError('Unknown stock version/build; no inferred update or downgrade')

def validate_package(image):
    subprocess.run([sys.executable,str(ROOT/'tools/stock/ValidateFirmwareLayout.py'),str(image),str(LAYOUT)],check=True)

def download_context():
    certificate=ROOT/'tools/certificates/Allterco.crt'
    metadata=json.loads((certificate.with_suffix('.json')).read_text())
    if hashlib.sha256(certificate.read_bytes()).hexdigest()!=metadata['sha256']:
        raise TakeoverError('Bundled stock CA identity differs; no download')
    context=ssl.create_default_context()
    context.load_verify_locations(cafile=str(certificate))
    return context

def prepare(image=None,opener=None):
    value=policy()
    if image is not None:
        image=Path(image);validate_package(image);return image
    directory=ROOT/'generated/StockFirmware';directory.mkdir(parents=True,exist_ok=True)
    image=directory/('PlugMG3-'+value['target']['version']+'.zip')
    if image.exists():validate_package(image);return image
    # Verify hostname/chain with the explicit public device CA; no insecure fallback.
    if opener is None:opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=download_context()))
    temporary=None
    try:
        with opener.open(value['target']['url'],timeout=60) as response:
            if response.geturl()!=value['target']['url']:raise TakeoverError('Stock download redirect refused')
            with tempfile.NamedTemporaryFile(dir=directory,suffix='.part',delete=False) as output:
                temporary=Path(output.name);count=0;digest=hashlib.sha256()
                while True:
                    block=response.read(65536)
                    if not block:break
                    count+=len(block)
                    if count>16*1024*1024:raise TakeoverError('Stock package exceeds download limit')
                    output.write(block);digest.update(block)
        expected=json.loads(LAYOUT.read_text())['package_sha256']
        if digest.hexdigest()!=expected:raise TakeoverError('Downloaded stock package identity differs')
        validate_package(temporary)
        temporary.replace(image);temporary=None
    except urllib.error.HTTPError as error:
        if error.code in (404,410):
            raise TakeoverError('Pinned stock package is no longer available at the configured URL; use an already fully validated official package. No device change.') from None
        raise TakeoverError('Stock download failed with HTTP status '+str(error.code)+'; no device change.') from None
    except urllib.error.URLError as error:
        if isinstance(error.reason,ssl.SSLCertVerificationError):
            raise TakeoverError('Stock HTTPS certificate chain could not be verified; no insecure fallback. Use an already fully validated official package or correct the PC certificate trust.') from None
        raise
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    print('Pinned stock package downloaded and verified; no device change.')
    return image

def wait_target(read_stock,expected_mac,timeout=420,clock=time.monotonic,sleep=time.sleep,stable_seconds=120):
    deadline=clock()+timeout
    stable_since=None;previous_uptime=None
    target=policy()['target']
    while clock()<deadline:
        try:public,current_mac=read_stock()
        except (urllib.error.URLError,TimeoutError,OSError,json.JSONDecodeError):
            stable_since=None;previous_uptime=None;sleep(2);continue
        if current_mac!=expected_mac:raise TakeoverError('Different device MAC after stock update; takeover blocked')
        classify(public)
        uptime=public.get('uptime')
        ready=((public.get('ver'),public.get('fw_id'))==(target['version'],target['build_id'])
            and public.get('slot')==0 and type(uptime) is int and uptime>=0)
        if not ready:
            stable_since=None;previous_uptime=None
        else:
            # Observe a continuous boot; this is not a manufacturer commit flag.
            if stable_since is None or previous_uptime is None or uptime<=previous_uptime:
                stable_since=clock()
            previous_uptime=uptime
            if clock()-stable_since>=stable_seconds and uptime>=stable_seconds:return
        sleep(2)
    raise TakeoverError('Pinned stock target not continuously stable in app_0; no retry update or takeover')

def update(http,expected_mac,image,read_stock,server_factory,local_address,wait=wait_target):
    validate_package(image)
    public,current_mac=read_stock()
    if current_mac!=expected_mac:raise TakeoverError('Device identity changed; no stock update')
    state=classify(public)
    if state=='ready':return
    ip=http.base.removeprefix('http://')
    with server_factory(ip,image) as server:
        url='http://'+local_address(ip)+':'+str(server.server.server_address[1])+'/Takeover.zip'
        payload=json.dumps({'id':1,'method':'Shelly.Update','params':{'url':url}},separators=(',',':')).encode()
        print('Sending the verified official stock update once; takeover waits for exact target and 120 seconds of stable app_0 uptime.',flush=True)
        try:
            reply=json.loads(http.request('/rpc',data=payload,headers={'Content-Type':'application/json'},timeout=30))
            if not isinstance(reply,dict) or reply.get('error') is not None:raise TakeoverError('Official stock update rejected; no takeover')
        except (urllib.error.URLError,TimeoutError,OSError,json.JSONDecodeError):
            print('Stock update reply unavailable; verifying without a second write.',flush=True)
        wait(read_stock,expected_mac)
        if not server.downloaded:raise TakeoverError('Stock target observed without a confirmed package transfer; takeover blocked')
    print('Same device confirmed on the exact stock target; takeover prerequisites will be checked again.')

if __name__=='__main__':
    try:prepare()
    except (TakeoverError,ValueError,KeyError,OSError,subprocess.CalledProcessError):
        error=sys.exc_info()[1];print(str(error) if isinstance(error,TakeoverError) else 'Pinned stock preparation failed; no insecure fallback or device action.',file=sys.stderr);raise SystemExit(1)
