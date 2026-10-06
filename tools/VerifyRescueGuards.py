#!/usr/bin/env python3
# VerifyRescueGuards.py, Version: 1.00
"""Compile actual Rescue guard functions with host flash/image mocks and real SHA256."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def extract(text, name):
    start = text.index(name)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


helper = extract((ROOT/'common/Rescue/EspRescueUpdater.cpp').read_text(), 'bool VerifyWrittenPayload(')
activation = extract((ROOT/'common/Rescue/main.cpp').read_text(), 'char const * RescueMainError(')
prelude = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
#include <openssl/sha.h>
constexpr int ESP_OK=0, ESP_PARTITION_TYPE_APP=0, ESP_PARTITION_SUBTYPE_APP_OTA_0=16, ESP_IMAGE_VERIFY=0;
struct esp_partition_t { uint32_t address; uint32_t size; };
struct esp_app_desc_t { char project_name[32]; };
struct esp_partition_pos_t { uint32_t offset; uint32_t size; };
struct esp_image_metadata_t {};
static esp_partition_t Partition={0x3a0000,4096};
static std::vector<uint8_t> Flash(4096);
static int FailureRead=-1, Reads=0;
static bool GeometryValid=true, PartitionPresent=true, DescriptorValid=true, ImageValid=true;
static const char * ProjectName="AnyMainApplication";
int esp_partition_read(const esp_partition_t *, size_t offset, void * data, size_t size) {
 if(Reads++==FailureRead) return -1;
 assert(offset+size<=Flash.size()); memcpy(data,Flash.data()+offset,size); return ESP_OK;
}
const esp_partition_t * esp_partition_find_first(int,int, const char *) { return PartitionPresent ? &Partition : nullptr; }
int esp_ota_get_partition_description(const esp_partition_t *,esp_app_desc_t * d) {
 if(!DescriptorValid) return -1;
 strncpy(d->project_name,ProjectName,31); return ESP_OK;
}
int esp_image_verify(int,const esp_partition_pos_t *p,esp_image_metadata_t *) {
 assert(p->offset==Partition.address && p->size==Partition.size); return ImageValid ? ESP_OK : -1;
}
class TEspSignedArtifactHash {
 std::vector<uint8_t> bytes;
 public:
 void Begin() { bytes.clear(); }
 void Add(const uint8_t *p,size_t n) { bytes.insert(bytes.end(),p,p+n); }
 bool EndAndCompare(const uint8_t expected[32]) {
  uint8_t actual[32]; SHA256(bytes.data(),bytes.size(),actual); return memcmp(actual,expected,32)==0;
 }
};
'''
tests = r'''
int main() {
 for(size_t i=0;i<Flash.size();++i) Flash[i]=uint8_t(i*17);
 uint8_t hash[32]; SHA256(Flash.data(),2051,hash);
 assert(VerifyWrittenPayload(&Partition,2051,hash)); assert(Reads==3);
 for(int i=0;i<3;++i) { Reads=0; FailureRead=i; assert(!VerifyWrittenPayload(&Partition,2051,hash)); }
 FailureRead=-1; Reads=0; Flash[2050]^=1; assert(!VerifyWrittenPayload(&Partition,2051,hash)); Flash[2050]^=1;
 assert(!VerifyWrittenPayload(nullptr,2051,hash)); assert(!VerifyWrittenPayload(&Partition,4097,hash));
 assert(RescueMainError()==nullptr);
 GeometryValid=false; assert(RescueMainError()!=nullptr); GeometryValid=true;
 PartitionPresent=false; assert(RescueMainError()!=nullptr); PartitionPresent=true;
 DescriptorValid=false; assert(RescueMainError()!=nullptr); DescriptorValid=true;
 ImageValid=false; assert(RescueMainError()!=nullptr); ImageValid=true;
 for(const char *name : {"ShellyTakeover","NousTakeover","ShellyReadout","TmrSwA8TTasmotaMigration"}) {
  ProjectName=name; assert(RescueMainError()!=nullptr);
 }
 ProjectName="IndependentApp"; assert(RescueMainError()==nullptr);
}
'''
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root/'test.cpp'
    source.write_text(prelude+'\n'+helper+'\n'+activation+'\n'+tests)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(source),'-lcrypto','-o',str(root/'test')],check=True)
    subprocess.run([str(root/'test')],check=True)
print('Actual Rescue guards passed: SHA256 readback/tamper/read faults, geometry/image rejection, transition rejection, independent Main.')
