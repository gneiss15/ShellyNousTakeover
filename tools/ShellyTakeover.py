#!/usr/bin/env python3
# ShellyTakeover.py, Version: 1.04
"""Check stock read-only; explicitly serve one OTA package and verify same-device Rescue."""
import argparse
import http.server
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import zipfile
import urllib.error
import urllib.request
from NousTakeover import Http,NoRedirect,TakeoverError,mac,wait_rescue
from ValidateTakeoverPackage import validate
import StockFirmware

ROOT=Path(__file__).resolve().parent.parent
class ShellyHttp(Http):
    def __init__(self,ip):
        self.base='http://'+str(ipaddress.IPv4Address(ip));self.auth=None
        passwords=urllib.request.HTTPPasswordMgrWithDefaultRealm()
        if os.environ.get('SHELLY_PASSWORD'):
            passwords.add_password(None,self.base,os.environ.get('SHELLY_USER','admin'),os.environ['SHELLY_PASSWORD'])
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPDigestAuthHandler(passwords))

def stock_state(http):
    public=json.loads(http.request('/shelly'))
    info=json.loads(http.request('/rpc/Shelly.GetDeviceInfo?ident=true'))
    if public.get('model')!='S3PL-30110EU' or public.get('app')!='PlugMG3' or info.get('model')!='S3PL-30110EU' or info.get('app')!='PlugMG3' or info.get('gen')!=3:
        raise TakeoverError('Unsupported Shelly model/generation; no upload')
    state=StockFirmware.classify(public)
    # Factory app_1 may update into app_0; ready Stock must already run in app_0.
    slot=public.get('slot')
    if (slot!=0 and not (slot==1 and state=='update_available')) or public.get('enhanced_security') is not False or info.get('fw_sbits') not in ('00','01'):
        raise TakeoverError('Unsupported active stock slot or security; no upload')
    device_mac=mac(info.get('mac'))
    if mac(public.get('mac'))!=device_mac:raise TakeoverError('Shelly device identity differs between endpoints')
    StockFirmware.classify(public)
    return public,device_mac

def preflight(http):
    public,device_mac=stock_state(http)
    if StockFirmware.classify(public)!='ready':
        raise TakeoverError('Checked stock update available; run --execute --update-stock to perform it before takeover')
    return device_mac

def stock_update_state(http):
    public,device_mac=stock_state(http)
    status=json.loads(http.request('/rpc/Sys.GetStatus'))
    public=dict(public);public['uptime']=status.get('uptime')
    return public,device_mac

class FirmwareServer:
    def __init__(self,ip,image,bind='0.0.0.0'):
        self.ip=ip;self.data=image.read_bytes();self.downloaded=False
        outer=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.client_address[0]!=outer.ip or self.path!='/Takeover.zip':self.send_error(404);return
                self.send_response(200);self.send_header('Content-Type','application/zip')
                self.send_header('Content-Length',str(len(outer.data)));self.send_header('Cache-Control','no-store');self.end_headers()
                try:self.wfile.write(outer.data);self.wfile.flush();outer.downloaded=True
                except (BrokenPipeError,ConnectionResetError):pass
        self.server=http.server.ThreadingHTTPServer((bind,0),Handler)
        self.server.daemon_threads=True
    def __enter__(self):
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.server.shutdown();self.server.server_close();self.thread.join()

def pc_address(device_ip):
    if os.environ.get('TAKEOVER_HTTP_HOST'):return str(ipaddress.IPv4Address(os.environ['TAKEOVER_HTTP_HOST']))
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as route:
        # UDP connect selects the interface without sending a datagram.
        route.connect((device_ip,80));return route.getsockname()[0]

def execute(http,expected_mac,image):
    validate(image)
    ip=http.base.removeprefix('http://')
    if preflight(http)!=expected_mac:raise TakeoverError('Device identity changed; no upload')
    with FirmwareServer(ip,image) as server:
        url='http://'+pc_address(ip)+':'+str(server.server.server_address[1])+'/Takeover.zip'
        payload=json.dumps({'id':1,'method':'Shelly.Update','params':{'url':url}},separators=(',',':')).encode()
        print('Serving validated package; requesting Shelly.Update once.',flush=True)
        try:
            reply=json.loads(http.request('/rpc',data=payload,headers={'Content-Type':'application/json'},timeout=30))
            if reply.get('error') is not None:
                error=reply['error'];code=error.get('code') if isinstance(error,dict) else None
                message=error.get('message') if isinstance(error,dict) else None
                # Only known constant messages; never echo arbitrary device response data.
                known=message if message in ('Not committed','Update in progress','No update in progress') else 'details suppressed'
                raise TakeoverError('Shelly.Update rejected the package; code='+str(code if isinstance(code,int) else 'unknown')+'; '+known+'; no retry')
        except (urllib.error.URLError,TimeoutError,OSError,json.JSONDecodeError):
            print('Update reply unavailable; watching status without another write.',flush=True)
        wait_rescue(http,expected_mac,target='shelly')
        if not server.downloaded:raise TakeoverError('Rescue reachable but package download was not confirmed; inspect state')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='serve package, request manufacturer OTA once and verify Rescue')
    parser.add_argument('--update-stock',action='store_true',help='allow the pinned official stock update before takeover; requires --execute')
    parser.add_argument('--stock-package',type=Path,help='use an existing official package after full identity/layout validation')
    args=parser.parse_args()
    if args.update_stock and not args.execute:raise TakeoverError('--update-stock requires --execute; default checks remain read-only')
    if args.stock_package and not args.update_stock:raise TakeoverError('--stock-package requires --update-stock')
    if not os.environ.get('SHELLY_IP'):raise TakeoverError('Set SHELLY_IP to the fixed station IPv4 address')
    http=ShellyHttp(os.environ['SHELLY_IP']);public,device_mac=stock_state(http)
    if StockFirmware.classify(public)=='update_available':
        if not args.execute:
            print('Checked official stock update available. Use --execute --update-stock to update, recheck and continue takeover. No device change.');return
        if not args.update_stock:raise TakeoverError('Stock update required; use --execute --update-stock to allow the checked path')
        # A missing/invalid Takeover must not be discovered after changing stock.
        validate(ROOT/'generated/ShellyTakeover/App/PlugMG3-ShellyTakeover.zip')
        image=StockFirmware.prepare(args.stock_package)
        StockFirmware.update(http,device_mac,image,lambda:stock_update_state(http),FirmwareServer,pc_address)
    if preflight(http)!=device_mac:raise TakeoverError('Device identity changed before takeover')
    print('Shelly stock/model/slot/security preflight passed; real flash/loader guards run inside Takeover.')
    if not args.execute:print('Read-only check completed; no upload.');return
    execute(http,device_mac,ROOT/'generated/ShellyTakeover/App/PlugMG3-ShellyTakeover.zip')
    print('Same device verified in Rescue; Main is not installed. Migration completed.')
if __name__=='__main__':
    try:main()
    except (TakeoverError,ValueError,KeyError,AssertionError,zipfile.BadZipFile,urllib.error.URLError,OSError,subprocess.CalledProcessError):
        error=sys.exc_info()[1];print(str(error) if isinstance(error,TakeoverError) else 'Device/package check failed; no automatic retry or reset.',file=sys.stderr);raise SystemExit(1)
