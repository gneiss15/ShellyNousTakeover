#!/usr/bin/env python3
# VerifyNousPc.py, Version: 1.01
"""Verify actual PC orchestration with synthetic HTTP responses; no device access."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import NousTakeover as pc

class Clock:
    value=0
    def now(self):return self.value
    def sleep(self,n):self.value+=n
class Http:
    base='http://192.0.2.10'
    def __init__(self):
        self.calls=[];self.responses=[];self.uploads=0;self.upload_error=False;self.safe=False
        self.values={'Status 2':{'StatusFWR':{'Version':'14.3.0.1(tasmota32)','BuildDateTime':'2024-11-05T10:09:04','Hardware':'ESP32-D0WD-V3'}},'Status 4':{'StatusMEM':{'FlashSize':4096}},'Status 5':{'StatusNET':{'IPAddress':'192.0.2.10','Mac':'02:00:00:00:00:01'}},'Template':{'NAME':'NOUS A8T','GPIO':[1,1,576,1,32,1,1,1,1,224,2624,1,1,1,1,1,0,1,1,1,0,1,2656,2720,0,0,0,0,1,1,1,1,1,0,0,1],'BASE':1,'FLAG':0},'Module':{'Module':{'0':'NOUS A8T'}}}
    def command(self,c):self.calls.append(c);return copy.deepcopy(self.values[c])
    def request(self,p,**kwargs):
        self.calls.append(p)
        if p=='/up':return b'<form action="u2?fsz="><input name="u2"></form>'
        if p=='/u4?api=1':return b'true'
        if p=='/u4?u4=fct&api=1':self.safe=True;return b'false'
        if p=='/':return b'<h3>SafeBoot</h3>' if self.safe else b'<h3>Main</h3>'
        if p.startswith('/u2?'):
            self.uploads+=1;assert b'name="u2"' in kwargs['data'] and b'firmware' in kwargs['data']
            if self.upload_error:raise urllib.error.URLError('lost reply')
            return b'<html>Upload response is not proof of Rescue</html>'
        if p=='/status':
            response=self.responses.pop(0)
            if isinstance(response,Exception):raise response
            return json.dumps(response).encode()
        raise AssertionError(p)
def rescue():return {'Application':'Rescue','Project':'NousTakeover','Version':'1.00','DeviceType':'TmrSwA8T','Mac':'020000000001','GeometryValid':True,'RunningOffset':0x10000,'BootOffset':0x10000,'MainReady':False}
class Test(unittest.TestCase):
    def test_read_only(self):
        h=Http();self.assertEqual(pc.preflight(h),'020000000001');self.assertEqual(h.uploads,0);self.assertFalse(h.safe)
        self.assertNotIn('/u4?u4=fct&api=1',h.calls)
    def test_denials(self):
        for command,key,change in [('Status 2','StatusFWR',{'Version':'11.0(tasmota32)'}),('Status 2','StatusFWR',{'BuildDateTime':'other'}),('Status 2','StatusFWR',{'Hardware':'ESP32-C3'}),('Status 4','StatusMEM',{'FlashSize':8192}),('Status 5','StatusNET',{'IPAddress':'192.168.4.1'}),('Module','Module',{'1':'Other'})]:
            h=Http();h.values[command][key].update(change)
            with self.assertRaises(pc.TakeoverError):pc.preflight(h)
            self.assertFalse(h.safe);self.assertEqual(h.uploads,0)
        h=Http();h.values['Template']['GPIO'][4]=224
        with self.assertRaises(pc.TakeoverError):pc.preflight(h)
    def test_rescue_denials(self):
        for field,value in [('Mac','020000000002'),('Project','Other'),('Version','other'),('DeviceType','other'),('GeometryValid',False),('BootOffset',0xE0000),('RunningOffset',0xE0000),('MainReady',True)]:
            s=rescue();s[field]=value
            with self.assertRaises(pc.TakeoverError):pc.rescue_verified(s,'020000000001')
    def test_failed_takeover(self):
        h=Http();h.responses=[{'Application':'NousTakeover','Phase':'Failed','Error':'unknown loader','RollbackVerified':False,'DoNotRestart':True}]
        clock=Clock()
        with self.assertRaises(pc.TakeoverError):pc.wait_rescue(h,'020000000001',clock=clock.now,sleep=clock.sleep)
    def test_upload_once(self):
        for lost_reply in [False,True]:
            h=Http();h.upload_error=lost_reply;h.responses=[{'Application':'NousTakeover','Phase':'WritingRescueAndMetadata'},urllib.error.URLError('restarting'),rescue()]
            clock=Clock()
            with tempfile.TemporaryDirectory() as t:
                image=Path(t)/'image.bin';image.write_bytes(b'firmware')
                with patch.object(pc.subprocess,'run') as validate,patch.object(pc,'wait_rescue',side_effect=lambda http,m:pc_wait(http,m,clock=clock.now,sleep=clock.sleep)):
                    pc.execute(h,'020000000001',image,clock=clock.now,sleep=clock.sleep)
                    validate.assert_called_once()
            self.assertEqual(h.uploads,1)
    def test_timeout(self):
        h=Http();h.responses=[{}]*3;clock=Clock()
        with self.assertRaises(pc.TakeoverError):pc.wait_rescue(h,'020000000001',timeout=5,clock=clock.now,sleep=clock.sleep)
    def test_invalid_image_before_switch(self):
        h=Http()
        with patch.object(pc.subprocess,'run',side_effect=pc.subprocess.CalledProcessError(1,'validation')):
            with self.assertRaises(pc.subprocess.CalledProcessError):pc.execute(h,'020000000001',Path('unused'))
        self.assertEqual(h.calls,[])
pc_wait=pc.wait_rescue
if __name__=='__main__':unittest.main()
