#!/usr/bin/env python3
# VerifyStockFirmware.py, Version: 1.03
"""Fault-test pinned stock preparation/update using synthetic transports; no device access."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import StockFirmware as stock
from NousTakeover import TakeoverError

POLICY=stock.policy()
def public(ready=False):
    source=POLICY['target'] if ready else POLICY['allowed_sources'][0]
    return {'model':POLICY['model'],'app':POLICY['app'],'ver':source['version'],'fw_id':source['build_id']}
class Clock:
    value=0
    def now(self):return self.value
    def sleep(self,n):self.value+=n
class Http:
    base='http://192.0.2.10'
    def __init__(self):self.writes=0;self.fail=False;self.reject=False
    def request(self,path,**kwargs):
        assert path=='/rpc';self.writes+=1
        value=json.loads(kwargs['data']);assert value['method']=='Shelly.Update'
        if self.fail:raise urllib.error.URLError('reply lost')
        return json.dumps({'error':{}} if self.reject else {'result':{}}).encode()
class Server:
    def __init__(self,*args):self.downloaded=True;self.server=type('Listener',(),{'server_address':('0.0.0.0',12345)})()
    def __enter__(self):return self
    def __exit__(self,*args):pass
class Test(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(stock.classify(public()),'update_available');self.assertEqual(stock.classify(public(True)),'ready')
        for change in [{'ver':'3.0.0'},{'fw_id':'unknown'},{'model':'other'},{'ver':'1.0.0'}]:
            value=public();value.update(change)
            with self.assertRaises(TakeoverError):stock.classify(value)
    def test_update_once(self):
        for lost in [False,True]:
            h=Http();h.fail=lost
            wait=lambda read,m:self.assertEqual(m,'020000000001')
            with patch.object(stock,'validate_package'):
                stock.update(h,'020000000001',Path('unused'),lambda:(public(),'020000000001'),Server,lambda ip:'192.0.2.20',wait=wait)
            self.assertEqual(h.writes,1)
    def test_no_write_on_denial(self):
        for read in [lambda:(public(),'other'),lambda:({'model':'unknown'},'020000000001')]:
            h=Http()
            with patch.object(stock,'validate_package'):
                with self.assertRaises(TakeoverError):stock.update(h,'020000000001',Path('unused'),read,Server,lambda ip:'192.0.2.20')
            self.assertEqual(h.writes,0)
    def test_rejected_rpc(self):
        h=Http();h.reject=True
        with patch.object(stock,'validate_package'):
            with self.assertRaises(TakeoverError):stock.update(h,'020000000001',Path('unused'),lambda:(public(),'020000000001'),Server,lambda ip:'192.0.2.20',wait=lambda *args:self.fail('must not monitor rejected RPC'))
        self.assertEqual(h.writes,1)
    def test_wait_target(self):
        clock=Clock()
        def read():
            value=public(clock.value>=2);value.update(slot=0,uptime=max(0,clock.value-2))
            return value,'020000000001'
        stock.wait_target(read,'020000000001',clock=clock.now,sleep=clock.sleep)
        self.assertEqual(clock.value,122)
        with self.assertRaises(TakeoverError):stock.wait_target(lambda:(public(True),'other'),'020000000001')
        clock=Clock()
        with self.assertRaises(TakeoverError):stock.wait_target(lambda:(public(),'020000000001'),'020000000001',timeout=3,clock=clock.now,sleep=clock.sleep)
    def test_readiness_resets(self):
        for event in ['restart','network','old_build','wrong_slot']:
            clock=Clock()
            def read():
                value=public(True);value.update(slot=0,uptime=clock.value+200)
                if clock.value==60:
                    if event=='network':raise urllib.error.URLError('synthetic interruption')
                    if event=='restart':value['uptime']=0
                    if event=='old_build':value=public()
                    if event=='wrong_slot':value['slot']=1
                if event=='restart' and clock.value>60:value['uptime']=clock.value-60
                return value,'020000000001'
            stock.wait_target(read,'020000000001',clock=clock.now,sleep=clock.sleep)
            self.assertEqual(clock.value,180 if event=='restart' else 182)
    def test_invalid_uptime_never_ready(self):
        for uptime in [None,True,-1,'120',120]:
            clock=Clock();value=public(True);value.update(slot=0,uptime=uptime)
            with self.assertRaises(TakeoverError):
                stock.wait_target(lambda:(value,'020000000001'),'020000000001',timeout=125,clock=clock.now,sleep=clock.sleep)
    def test_existing_file_is_verified(self):
        with patch.object(stock,'validate_package') as validate:
            self.assertEqual(stock.prepare(Path('existing.zip')),Path('existing.zip'));validate.assert_called_once_with(Path('existing.zip'))
    def test_download_cleanup_and_publish(self):
        for corrupt,redirect,layout_failure in [(False,False,False),(True,False,False),(False,True,False),(False,False,True)]:
            with tempfile.TemporaryDirectory() as t:
                root=Path(t);data=b'synthetic stock zip'
                layout=root/'layout.json';layout.write_text(json.dumps({'package_sha256':hashlib.sha256(data).hexdigest()}))
                class Response(io.BytesIO):
                    def geturl(self):return 'https://other.invalid/' if redirect else POLICY['target']['url']
                class Opener:
                    def open(self,url,timeout):assert url==POLICY['target']['url'];return Response(data+b'wrong' if corrupt else data)
                def validate(path):
                    self.assertEqual(path.read_bytes(),data)
                    if layout_failure:raise TakeoverError('layout mismatch')
                with patch.object(stock,'ROOT',root),patch.object(stock,'LAYOUT',layout),patch.object(stock,'policy',return_value=POLICY),patch.object(stock,'validate_package',side_effect=validate):
                    if corrupt or redirect or layout_failure:
                        with self.assertRaises(TakeoverError):stock.prepare(opener=Opener())
                        self.assertEqual(list((root/'generated/StockFirmware').glob('*')),[])
                    else:
                        image=stock.prepare(opener=Opener());self.assertEqual(image.read_bytes(),data)
                        self.assertEqual(len(list(image.parent.glob('*'))),1)
    def test_older_ready_is_not_update_confirmation(self):
        old=POLICY['accepted_stock'][0]
        value={'model':POLICY['model'],'app':POLICY['app'],'ver':old['version'],'fw_id':old['build_id']}
        self.assertEqual(stock.classify(value),'ready')
        clock=Clock()
        with self.assertRaises(TakeoverError):
            stock.wait_target(lambda:(value,'020000000001'),'020000000001',timeout=3,clock=clock.now,sleep=clock.sleep)
    def test_public_ca(self):
        context=stock.download_context()
        import ssl
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'tools/certificates';folder.mkdir(parents=True)
            (folder/'Allterco.crt').write_bytes(b'corrupt')
            (folder/'Allterco.json').write_text((stock.ROOT/'tools/certificates/Allterco.json').read_text())
            with patch.object(stock,'ROOT',root),self.assertRaises(TakeoverError):stock.download_context()
    def test_missing_download(self):
        for code in (404,410,500):
            class Opener:
                def open(self,url,timeout):
                    raise urllib.error.HTTPError(url,code,'synthetic failure',{},None)
            with tempfile.TemporaryDirectory() as directory, patch.object(stock,'ROOT',Path(directory)):
                with self.assertRaisesRegex(TakeoverError,'no longer available' if code in (404,410) else 'HTTP status 500'):
                    stock.prepare(opener=Opener())
                self.assertEqual(list((Path(directory)/'generated/StockFirmware').glob('*')),[])
    def test_invalid_url(self):
        actual=json.loads(stock.POLICY.read_text())
        for url in ['http://fwcdn.shelly.cloud/file','https://other.invalid/file','https://user:secret@fwcdn.shelly.cloud/file']:
            value=json.loads(json.dumps(actual));value['target']['url']=url
            with tempfile.TemporaryDirectory() as t:
                p=Path(t)/'policy.json';p.write_text(json.dumps(value))
                with patch.object(stock,'POLICY',p):
                    with self.assertRaises(TakeoverError):stock.policy()
if __name__=='__main__':unittest.main()
