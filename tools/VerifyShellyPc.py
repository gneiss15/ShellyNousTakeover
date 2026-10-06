#!/usr/bin/env python3
# VerifyShellyPc.py, Version: 1.06
"""Exercise actual Shelly PC orchestration and one-file HTTP server without hardware."""
import json
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import ShellyTakeover as pc
from NousTakeover import rescue_verified
class Http:
    base='http://192.0.2.10'
    def __init__(self):
        self.writes=0;self.reply={'result':{}};self.lost=False
        self.public={'model':'S3PL-30110EU','app':'PlugMG3','ver':'2.0.0','fw_id':'20260710-101147/2.0.0-g87fbfa4','slot':0,'enhanced_security':False,'mac':'020000000001'}
        self.info={'model':'S3PL-30110EU','app':'PlugMG3','gen':3,'fw_sbits':'00','mac':'020000000001'}
    def request(self,path,**kwargs):
        if path=='/shelly':return json.dumps(self.public).encode()
        if path.startswith('/rpc/Shelly.GetDeviceInfo'):return json.dumps(self.info).encode()
        if path=='/rpc/Sys.GetStatus':return json.dumps({'uptime':180}).encode()
        assert path=='/rpc';self.writes+=1
        payload=json.loads(kwargs['data']);assert payload['method']=='Shelly.Update' and payload['params']['url'].endswith('/Takeover.zip')
        if self.lost:raise urllib.error.URLError('lost reply')
        return json.dumps(self.reply).encode()
class FakeServer:
    def __init__(self,*args):self.downloaded=True;self.server=type('Server',(),{'server_address':('0.0.0.0',12345)})()
    def __enter__(self):return self
    def __exit__(self,*args):pass
class Test(unittest.TestCase):
    def test_preflight(self):
        h=Http();self.assertEqual(pc.preflight(h),'020000000001');self.assertEqual(h.writes,0)
        target=pc.StockFirmware.policy()['target'];h.public.update(ver=target['version'],fw_id=target['build_id'])
        self.assertEqual(pc.preflight(h),'020000000001');self.assertEqual(h.writes,0)
        for field,value in [('model','Other'),('ver','1.0'),('fw_id','other'),('slot',1),('enhanced_security',True),('mac','020000000002')]:
            h=Http();h.public[field]=value
            with self.assertRaises(pc.TakeoverError):pc.preflight(h)
            self.assertEqual(h.writes,0)
        for field,value in [('gen',2),('fw_sbits','ff'),('app','Other')]:
            h=Http();h.info[field]=value
            with self.assertRaises(pc.TakeoverError):pc.preflight(h)
    def test_stock_uptime_reader(self):
        h=Http();value,identity=pc.stock_update_state(h)
        self.assertEqual(value['uptime'],180);self.assertEqual(identity,'020000000001')
        self.assertNotIn('uptime',h.public);self.assertEqual(h.writes,0)
    def test_factory_slot_one_only_before_update(self):
        h=Http();source=pc.StockFirmware.policy()['allowed_sources'][0]
        h.public.update(ver=source['version'],fw_id=source['build_id'],slot=1)
        self.assertEqual(pc.stock_state(h)[1],'020000000001')
        with self.assertRaises(pc.TakeoverError):pc.preflight(h)
        h.public['slot']=2
        with self.assertRaises(pc.TakeoverError):pc.stock_state(h)
        h.public['slot']=1;h.public['enhanced_security']=True
        with self.assertRaises(pc.TakeoverError):pc.stock_state(h)
        self.assertEqual(h.writes,0)
    def test_update_once(self):
        for lost in [False,True]:
            h=Http();h.lost=lost
            with patch.object(pc,'validate'),patch.object(pc,'FirmwareServer',FakeServer),patch.object(pc,'pc_address',return_value='192.0.2.20'),patch.object(pc,'wait_rescue') as monitor:
                pc.execute(h,'020000000001',Path('unused'));monitor.assert_called_once_with(h,'020000000001',target='shelly')
            self.assertEqual(h.writes,1)
    def test_rpc_rejection(self):
        h=Http();h.reply={'error':{'code':-1,'message':'Not committed'}}
        with patch.object(pc,'validate'),patch.object(pc,'FirmwareServer',FakeServer),patch.object(pc,'pc_address',return_value='192.0.2.20'),patch.object(pc,'wait_rescue') as monitor:
            with self.assertRaisesRegex(pc.TakeoverError,'code=-1; Not committed'):pc.execute(h,'020000000001',Path('unused'))
            monitor.assert_not_called()
        self.assertEqual(h.writes,1)
    def test_rescue(self):
        s={'Application':'Rescue','Project':'ShellyTakeover','Version':'1.00','DeviceType':'TmrSwShellyC3V1','Mac':'020000000001','GeometryValid':True,'RunningOffset':0x640000,'BootOffset':0x640000,'MainReady':False}
        self.assertTrue(rescue_verified(s,'020000000001','shelly'))
        with patch.dict(os.environ,{'TAKEOVER_DEVICE_TYPE':'CustomShellyV1'}):
            with self.assertRaises(pc.TakeoverError):rescue_verified(s,'020000000001','shelly')
            s['DeviceType']='CustomShellyV1';self.assertTrue(rescue_verified(s,'020000000001','shelly'))
        s['DeviceType']='TmrSwShellyC3V1'
        s['BootOffset']=0x10000
        with self.assertRaises(pc.TakeoverError):rescue_verified(s,'020000000001','shelly')
    def test_stock_before_takeover(self):
        source=pc.StockFirmware.policy()['allowed_sources'][0]
        for outcome in ['ok','failed','wrong_mac','still_old']:
            h=Http();h.public.update(ver=source['version'],fw_id=source['build_id'])
            def update(*args):
                if outcome=='failed':raise pc.TakeoverError('stock update failed')
                if outcome!='still_old':
                    target=pc.StockFirmware.policy()['target'];h.public.update(ver=target['version'],fw_id=target['build_id'])
                if outcome=='wrong_mac':h.public['mac']=h.info['mac']='020000000002'
            with patch.dict(os.environ,{'SHELLY_IP':'192.0.2.10'}),patch.object(sys,'argv',['ShellyTakeover.py','--execute','--update-stock']),patch.object(pc,'ShellyHttp',return_value=h),patch.object(pc,'validate'),patch.object(pc.StockFirmware,'prepare',return_value=Path('stock.zip')),patch.object(pc.StockFirmware,'update',side_effect=update),patch.object(pc,'execute') as takeover:
                if outcome=='ok':pc.main();takeover.assert_called_once()
                else:
                    with self.assertRaises(pc.TakeoverError):pc.main()
                    takeover.assert_not_called()
    def test_stock_offer_is_read_only(self):
        h=Http();source=pc.StockFirmware.policy()['allowed_sources'][0]
        h.public.update(ver=source['version'],fw_id=source['build_id'])
        with patch.dict(os.environ,{'SHELLY_IP':'192.0.2.10'}),patch.object(sys,'argv',['ShellyTakeover.py']),patch.object(pc,'ShellyHttp',return_value=h),patch.object(pc.StockFirmware,'prepare') as download,patch.object(pc.StockFirmware,'update') as update,patch.object(pc,'execute') as takeover:
            pc.main();download.assert_not_called();update.assert_not_called();takeover.assert_not_called()
        self.assertEqual(h.writes,0)
    def test_file_server(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'image.zip';p.write_bytes(b'synthetic zip')
            with pc.FirmwareServer('127.0.0.1',p,bind='127.0.0.1') as server:
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                base='http://127.0.0.1:'+str(server.server.server_address[1])
                self.assertEqual(opener.open(base+'/Takeover.zip').read(),b'synthetic zip')
                self.assertTrue(server.downloaded)
                for path in ['/','/other','/../image.zip','/Takeover.zip?other']:
                    with self.assertRaises(urllib.error.HTTPError) as error:opener.open(base+path)
                    self.assertEqual(error.exception.code,404)
if __name__=='__main__':unittest.main()
