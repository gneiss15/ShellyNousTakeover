// EspSignedArtifact.h, Version: 1.00
#pragma once

#include <Arduino.h>
#include <cstddef>
#include <cstdint>

#include <mbedtls/sha256.h>

enum class TEspSignedArtifactType : uint8_t
 {
  Firmware = 1,
  FileSystem = 2,
  Combined = 3,
  Config = 4,
  Rescue = 5
 };

struct TEspSignedArtifactInfo
 {
  uint32_t PayloadSize;
  uint32_t PayloadOffset;
  uint16_t SignatureSize;
  uint8_t PayloadHash[32];
 };

class TEspSignedArtifactHash
 {
 public:
                    TEspSignedArtifactHash(void);
                   ~TEspSignedArtifactHash(void);
  void              Begin(void);
  void              Add( void const * Data, size_t Size );
  bool              EndAndCompare( uint8_t const ExpectedHash[32] );

 private:
  mbedtls_sha256_context FContext;
  bool                   FStarted;
 };

size_t EspSignedArtifactPrefixSize( uint16_t SignatureSize );
bool EspSignedArtifactReadSignatureSize( uint8_t const * Prefix, size_t PrefixSize,
  uint16_t & SignatureSize, String & Error );
bool EspSignedArtifactVerifyPrefix( uint8_t const * Prefix, size_t PrefixSize,
  TEspSignedArtifactType ExpectedType, char const * ExpectedDeviceType,
  uint32_t TotalSize, uint32_t MaximumPayloadSize,
  TEspSignedArtifactInfo & Info, String & Error );
