// EspSignedArtifact.cpp, Version: 1.01
#include "EspSignedArtifact.h"
#include "EspUpdatePublicKey.h"

#include <cstring>

#include <mbedtls/pk.h>

namespace
 {
  uint8_t const DeviceTypeMagic[8] = { 'E', 'S', 'P', 'D', 'T', '0', '1', 0 };
  uint8_t const SignatureMagic[8] = { 'E', 'S', 'P', 'S', 'I', 'G', '0', '1' };
  constexpr size_t DeviceTypeHeaderSize = 64;
  constexpr size_t SignatureHeaderSize = 48;
  constexpr uint8_t DeviceTypeFormatVersion = 1;
  constexpr uint8_t SignatureFormatVersion = 1;
  constexpr uint8_t SignatureHashSha256 = 1;

  uint16_t ReadUInt16Le( uint8_t const * Data )
   {
    return uint16_t( Data[0] ) |
      uint16_t( Data[1] ) << 8;
   }

  uint32_t ReadUInt32Le( uint8_t const * Data )
   {
    return uint32_t( Data[0] ) |
      uint32_t( Data[1] ) << 8 |
      uint32_t( Data[2] ) << 16 |
      uint32_t( Data[3] ) << 24;
   }

  bool VerifyManifestSignature( uint8_t const * Manifest, size_t ManifestSize,
    uint8_t const * Signature, size_t SignatureSize )
   {
    uint8_t Hash[32];
    if( mbedtls_sha256( Manifest, ManifestSize, Hash, 0 ) != 0 )
      return false;

    mbedtls_pk_context PublicKey;
    mbedtls_pk_init( &PublicKey );
    const int ParseResult = mbedtls_pk_parse_public_key( &PublicKey,
      EspUpdatePublicKey::Data, EspUpdatePublicKey::Size );
    if( ParseResult != 0 )
     {
      mbedtls_pk_free( &PublicKey );
      return false;
     }

    const int VerifyResult = mbedtls_pk_verify( &PublicKey, MBEDTLS_MD_SHA256,
      Hash, sizeof( Hash ), Signature, SignatureSize );
    mbedtls_pk_free( &PublicKey );
    return VerifyResult == 0;
   }
 }

TEspSignedArtifactHash::TEspSignedArtifactHash(void)
 : FStarted( false )
 {
  mbedtls_sha256_init( &FContext );
 }

TEspSignedArtifactHash::~TEspSignedArtifactHash(void)
 {
  mbedtls_sha256_free( &FContext );
 }

void TEspSignedArtifactHash::Begin(void)
 {
  mbedtls_sha256_starts( &FContext, 0 );
  FStarted = true;
 }

void TEspSignedArtifactHash::Add( void const * Data, size_t Size )
 {
  if( FStarted && Size )
    mbedtls_sha256_update( &FContext,
      static_cast<unsigned char const *>( Data ), Size );
 }

bool TEspSignedArtifactHash::EndAndCompare( uint8_t const ExpectedHash[32] )
 {
  if( !FStarted )
    return false;
  uint8_t Hash[32];
  FStarted = false;
  if( mbedtls_sha256_finish( &FContext, Hash ) != 0 )
    return false;
  return memcmp( Hash, ExpectedHash, sizeof( Hash ) ) == 0;
 }

size_t EspSignedArtifactPrefixSize( uint16_t SignatureSize )
 {
  return DeviceTypeHeaderSize + SignatureHeaderSize + SignatureSize;
 }

bool EspSignedArtifactReadSignatureSize( uint8_t const * Prefix, size_t PrefixSize,
  uint16_t & SignatureSize, String & Error )
 {
  if( PrefixSize < DeviceTypeHeaderSize + SignatureHeaderSize )
   {
    Error = F( "Signed artifact header is incomplete" );
    return false;
   }

  uint8_t const * SignatureHeader = Prefix + DeviceTypeHeaderSize;
  if( memcmp( SignatureHeader, SignatureMagic, sizeof( SignatureMagic ) ) != 0 ||
      ReadUInt16Le( SignatureHeader + 8 ) != SignatureHeaderSize ||
      SignatureHeader[10] != SignatureFormatVersion ||
      SignatureHeader[11] != SignatureHashSha256 )
   {
    Error = F( "Invalid signed-artifact header" );
    return false;
   }

  const uint32_t Size = ReadUInt32Le( SignatureHeader + 12 );
  if( Size == 0 || Size > UINT16_MAX )
   {
    Error = F( "Invalid RSA signature size" );
    return false;
   }
  SignatureSize = uint16_t( Size );
  return true;
 }

bool EspSignedArtifactVerifyPrefix( uint8_t const * Prefix, size_t PrefixSize,
  TEspSignedArtifactType ExpectedType, char const * ExpectedDeviceType,
  uint32_t TotalSize, uint32_t MaximumPayloadSize,
  TEspSignedArtifactInfo & Info, String & Error )
 {
  uint16_t SignatureSize = 0;
  if( !EspSignedArtifactReadSignatureSize( Prefix, PrefixSize, SignatureSize, Error ) )
    return false;

  const size_t RequiredPrefixSize = EspSignedArtifactPrefixSize( SignatureSize );
  if( PrefixSize < RequiredPrefixSize )
   {
    Error = F( "RSA signature is incomplete" );
    return false;
   }

  if( memcmp( Prefix, DeviceTypeMagic, sizeof( DeviceTypeMagic ) ) != 0 ||
      ReadUInt16Le( Prefix + 8 ) != DeviceTypeHeaderSize ||
      Prefix[10] != DeviceTypeFormatVersion )
   {
    Error = F( "Invalid DeviceType header" );
    return false;
   }
  if( Prefix[11] != uint8_t( ExpectedType ) )
   {
    Error = F( "Artifact type mismatch" );
    return false;
   }

  char DeviceType[33];
  memcpy( DeviceType, Prefix + 16, 32 );
  DeviceType[32] = 0;
  char * Terminator = static_cast<char *>( memchr( DeviceType, 0, 32 ) );
  if( !Terminator || Terminator == DeviceType || !ExpectedDeviceType ||
      strcmp( DeviceType, ExpectedDeviceType ) != 0 )
   {
    Error = F( "DeviceType mismatch" );
    return false;
   }
  for( uint8_t const * Reserved = Prefix + 48;
       Reserved != Prefix + DeviceTypeHeaderSize; ++Reserved )
   {
    if( *Reserved )
     {
      Error = F( "Unsupported DeviceType header extension" );
      return false;
     }
   }

  const uint32_t PayloadSize = ReadUInt32Le( Prefix + 12 );
  if( PayloadSize == 0 || PayloadSize > MaximumPayloadSize )
   {
    Error = F( "Payload size is invalid" );
    return false;
   }
  if( TotalSize && uint64_t( RequiredPrefixSize ) + PayloadSize != TotalSize )
   {
    Error = F( "Signed artifact size mismatch" );
    return false;
   }

  if( !VerifyManifestSignature( Prefix, DeviceTypeHeaderSize + SignatureHeaderSize,
       Prefix + DeviceTypeHeaderSize + SignatureHeaderSize, SignatureSize ) )
   {
    Error = F( "RSA signature verification failed" );
    return false;
   }

  Info.PayloadSize = PayloadSize;
  Info.PayloadOffset = RequiredPrefixSize;
  Info.SignatureSize = SignatureSize;
  memcpy( Info.PayloadHash, Prefix + DeviceTypeHeaderSize + 16,
    sizeof( Info.PayloadHash ) );
  return true;
 }
