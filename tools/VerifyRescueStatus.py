#!/usr/bin/env python3
# VerifyRescueStatus.py, Version: 1.01
"""Compile the actual read-only status route with SDK/socket mocks; no device access."""
from pathlib import Path
import json
import subprocess
import tempfile
root=Path(__file__).resolve().parent.parent
source=(root/'common/Rescue/EspRescueUpdater.cpp').read_text()
a=source.index('  if( !IsPost && strcmp( Path, "/status" ) == 0 )')
b=source.index('\n  if( IsPost && strcmp( Path, "/Firmware" )',a)
branch=source[a:b]
prelude=r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <cassert>
#define ESP_OK 0
#define ESP_MAC_WIFI_STA 0
#define ESP_UPDATE_DEVICE_TYPE "TmrSwA8T"
struct esp_partition_t { unsigned address; };
static esp_partition_t Rescue={0x10000};
static bool Geometry=true,MainReady=false,MacOk=true,BootPresent=true;
static std::string Response;static int ErrorStatus;
static const char * FProjectName="NousTakeover",*FRescueVersion="1.00";
static int esp_read_mac(uint8_t * Mac,int Type){assert(Type==0);memset(Mac,0,6);Mac[0]=2;Mac[5]=1;return MacOk?0:-1;}
static const esp_partition_t * esp_ota_get_running_partition(void){return &Rescue;}
static const esp_partition_t * esp_ota_get_boot_partition(void){return BootPresent?&Rescue:nullptr;}
static bool RescueGeometryValid(void){return Geometry;}
static const char * RescueMainError(void){return MainReady?nullptr:"not installed";}
static void SendText(int Socket,int Code,const char * Text){(void)Socket;(void)Text;ErrorStatus=Code;}
static bool SendAll(int Socket,const char * Text){(void)Socket;Response+=Text;return true;}
static bool Handle(void){bool IsPost=false;const char * Path="/status";int ClientSocket=1;
'''
tests=r'''
return false;}
static void output(void){Response.clear();ErrorStatus=0;assert(Handle()&&ErrorStatus==0);auto Start=Response.find("\r\n\r\n");assert(Start!=std::string::npos);puts(Response.substr(Start+4).c_str());}
int main(void){output();Geometry=false;output();Geometry=true;MainReady=true;output();MainReady=false;BootPresent=false;output();
 MacOk=false;assert(!Handle()&&ErrorStatus==500);MacOk=true;
 std::string Huge(600,'x');FProjectName=Huge.c_str();assert(!Handle()&&ErrorStatus==500);
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.cpp').write_text(prelude+branch+tests)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 rows=[json.loads(line) for line in subprocess.check_output([str(p/'test')],text=True).splitlines()]
 assert len(rows)==4 and rows[0]['Mac']=='020000000001' and rows[0]['GeometryValid'] is True
 assert rows[0]['Application']=='Rescue' and rows[0]['Project']=='NousTakeover' and rows[0]['DeviceType']=='TmrSwA8T'
 assert rows[0]['BootOffset']==rows[0]['RunningOffset']==0x10000 and rows[0]['MainReady'] is False
 assert rows[1]['GeometryValid'] is False and rows[2]['MainReady'] is True and rows[3]['BootOffset']==0
print('Actual Rescue status route passed: JSON, MAC/project/type, geometry, boot target, Main-ready, identity failure and response bounds. SDK/socket mocks; no hardware test.')
