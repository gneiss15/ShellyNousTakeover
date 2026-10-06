// EspRescueUpdater.cpp, Version: 2.14
#include "EspRescueUpdater.h"
#include "RescueGuard.h"
#include "DeviceType.inc.h"
#include "EspSignedArtifact.h"

#include <cerrno>
#include <cstring>
#include <cstdio>
#include <esp_mac.h>
#include <fcntl.h>
#include <sys/time.h>
#include <unistd.h>

#include <esp_system.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <lwip/inet.h>
#include <lwip/sockets.h>

namespace
 {
  constexpr int HttpTimeoutSeconds = 10;

  bool VerifyWrittenPayload(esp_partition_t const * Partition, uint32_t Size,
    uint8_t const ExpectedHash[32])
   {
    if( !Partition || Size > Partition->size ) return false;
    TEspSignedArtifactHash Hash;
    Hash.Begin();
    uint8_t Buffer[1024];
    uint32_t Offset = 0;
    while( Offset < Size )
     {
      const size_t Count = Size - Offset < sizeof(Buffer) ? Size - Offset : sizeof(Buffer);
      if( esp_partition_read(Partition, Offset, Buffer, Count) != ESP_OK ) return false;
      Hash.Add(Buffer, Count);
      Offset += Count;
     }
    return Hash.EndAndCompare(ExpectedHash);
   }


  bool IsContentLengthHeader( char const * Line )
   {
    constexpr char Name[] = "content-length:";
    for( size_t Index = 0; Index < sizeof( Name ) - 1; ++Index )
     {
      char Ch = Line[Index];
      if( Ch >= 'A' && Ch <= 'Z' )
        Ch += 'a' - 'A';
      if( Ch != Name[Index] )
        return false;
     }
    return true;
   }

  bool ParseUInt32( char const * Text, uint32_t & Value )
   {
    while( *Text == ' ' || *Text == '\t' )
      ++Text;
    if( *Text < '0' || *Text > '9' )
      return false;

    uint32_t Result = 0;
    while( *Text >= '0' && *Text <= '9' )
     {
      const uint32_t Digit = uint32_t( *Text - '0' );
      if( Result > (UINT32_MAX - Digit) / 10 )
        return false;
      Result = Result * 10 + Digit;
      ++Text;
     }
    Value = Result;
    return true;
   }

  char const * StatusLine( int Status )
   {
    switch( Status )
     {
      case 200: return "HTTP/1.1 200 OK\r\n";
      case 400: return "HTTP/1.1 400 Bad Request\r\n";
      case 404: return "HTTP/1.1 404 Not Found\r\n";
      case 411: return "HTTP/1.1 411 Length Required\r\n";
      default:  return "HTTP/1.1 500 Internal Server Error\r\n";
     }
   }
 }

TEspRescueUpdater::TEspRescueUpdater(void)
 : FServerSocket( -1 )
 , FProjectName( "ESP" )
 , FRescueVersion( "?" )
 , FMainPartition( nullptr )
 , FFileSystemPartition( nullptr )
 , FUpdateCompleted( false )
 {
 }

bool TEspRescueUpdater::Setup( char const * ProjectName,
  char const * RescueVersion )
 {
  FProjectName = ProjectName ? ProjectName : "ESP";
  FRescueVersion = RescueVersion ? RescueVersion : "?";
  FMainPartition = esp_partition_find_first(
    ESP_PARTITION_TYPE_APP, ESP_PARTITION_SUBTYPE_APP_OTA_0, nullptr );
  FFileSystemPartition = esp_partition_find_first(
    ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_SPIFFS, nullptr );

  // Once Rescue is running it stays the boot target until Commit succeeds.
  RestoreRescueBoot();

  FServerSocket = socket( AF_INET, SOCK_STREAM, IPPROTO_IP );
  if( FServerSocket < 0 )
    return false;

  int ReuseAddress = 1;
  setsockopt( FServerSocket, SOL_SOCKET, SO_REUSEADDR,
    &ReuseAddress, sizeof( ReuseAddress ) );

  sockaddr_in Address = {};
  Address.sin_family = AF_INET;
  Address.sin_port = htons( 80 );
  Address.sin_addr.s_addr = htonl( INADDR_ANY );
  if( bind( FServerSocket, reinterpret_cast<sockaddr *>( &Address ),
            sizeof( Address ) ) != 0 ||
      listen( FServerSocket, 2 ) != 0 )
   {
    close( FServerSocket );
    FServerSocket = -1;
    return false;
   }

  const int Flags = fcntl( FServerSocket, F_GETFL, 0 );
  if( Flags >= 0 )
    fcntl( FServerSocket, F_SETFL, Flags | O_NONBLOCK );
  return true;
 }

bool TEspRescueUpdater::HandleClient( int ClientSocket )
 {
  char Request[96];
  if( !ReadLine( ClientSocket, Request, sizeof( Request ) ) )
    return false;

  char * Path;
  bool IsPost;
  if( strncmp( Request, "GET ", 4 ) == 0 )
   {
    IsPost = false;
    Path = Request + 4;
   }
   else if( strncmp( Request, "POST ", 5 ) == 0 )
   {
    IsPost = true;
    Path = Request + 5;
   }
   else
   {
    SendText( ClientSocket, 400, "Unsupported HTTP method" );
    return false;
   }

  char * End = strchr( Path, ' ' );
  if( !End )
   {
    SendText( ClientSocket, 400, "Invalid HTTP request" );
    return false;
   }
  *End = 0;
  if( char * Query = strchr( Path, '?' ) )
    *Query = 0;

  uint32_t ContentLength = 0;
  if( !ReadHeaders( ClientSocket, ContentLength ) )
   {
    SendText( ClientSocket, 400, "Invalid HTTP headers" );
    return false;
   }

  if( !IsPost && (strcmp( Path, "/" ) == 0 ||
                   strcmp( Path, "/Index.html" ) == 0) )
   {
    SendRecoveryPage( ClientSocket );
    return true;
   }

  if( !IsPost && strcmp( Path, "/status" ) == 0 )
   {
    uint8_t Mac[6] = {};
    if( esp_read_mac(Mac, ESP_MAC_WIFI_STA) != ESP_OK )
     {
      SendText(ClientSocket, 500, "Cannot read device identity");
      return false;
     }
    const esp_partition_t * Running = esp_ota_get_running_partition();
    const esp_partition_t * Boot = esp_ota_get_boot_partition();
    char Json[512];
    // Project/version/device type are fixed build constants, not external input.
    int Length = snprintf(Json, sizeof(Json),
      "{\"Application\":\"Rescue\",\"Project\":\"%s\",\"Version\":\"%s\","
      "\"DeviceType\":\"%s\",\"Mac\":\"%02X%02X%02X%02X%02X%02X\","
      "\"GeometryValid\":%s,\"RunningOffset\":%lu,\"BootOffset\":%lu,\"MainReady\":%s}",
      FProjectName, FRescueVersion, ESP_UPDATE_DEVICE_TYPE,
      Mac[0], Mac[1], Mac[2], Mac[3], Mac[4], Mac[5],
      RescueGeometryValid() ? "true" : "false",
      (unsigned long)(Running ? Running->address : 0),
      (unsigned long)(Boot ? Boot->address : 0), RescueMainError() ? "false" : "true");
    if( Length < 0 || size_t(Length) >= sizeof(Json) )
     {
      SendText(ClientSocket, 500, "Status encoding failed");
      return false;
     }
    return SendAll(ClientSocket, "HTTP/1.1 200 OK\r\nConnection: close\r\n"
      "Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n") && SendAll(ClientSocket, Json);
   }

  if( IsPost && strcmp( Path, "/Firmware" ) == 0 )
    return HandleUpdate( ClientSocket, TPart::Firmware, ContentLength );
  if( IsPost && strcmp( Path, "/Filesystem" ) == 0 )
    return HandleUpdate( ClientSocket, TPart::FileSystem, ContentLength );
  if( IsPost && strcmp( Path, "/Commit" ) == 0 )
   {
    HandleCommit( ClientSocket );
    return true;
   }
  if( IsPost && strcmp( Path, "/Main" ) == 0 )
   {
    HandleMain( ClientSocket );
    return true;
   }

  SendText( ClientSocket, 404, "Not found" );
  return false;
 }

bool TEspRescueUpdater::HandleUpdate( int ClientSocket,
  TPart Part, uint32_t ContentLength )
 {
  if( !RescueGeometryValid() ) { SendText(ClientSocket, 400, "Geometry rejected; updates disabled"); return false; }
  FUpdateCompleted = false;
  constexpr size_t FixedPrefixSize = 64 + 48;
  constexpr size_t MaximumSignatureSize = 512;
  uint8_t Prefix[FixedPrefixSize + MaximumSignatureSize];
  if( ContentLength < FixedPrefixSize ||
      !ReadExact( ClientSocket, Prefix, FixedPrefixSize ) )
   {
    SendText( ClientSocket, ContentLength ? 400 : 411,
      "Signed artifact header is incomplete" );
    return false;
   }

  uint16_t SignatureSize = 0;
  String Error;
  if( !EspSignedArtifactReadSignatureSize( Prefix, FixedPrefixSize,
       SignatureSize, Error ) || SignatureSize > MaximumSignatureSize )
   {
    SendText( ClientSocket, 400, Error.length() ? Error.c_str() :
      "RSA signature is too large" );
    return false;
   }
  if( !ReadExact( ClientSocket, Prefix + FixedPrefixSize, SignatureSize ) )
   {
    SendText( ClientSocket, 400, "RSA signature is incomplete" );
    return false;
   }

  const uint32_t MaximumPayloadSize = Part == TPart::Firmware ?
    (FMainPartition ? FMainPartition->size : 0) :
    (FFileSystemPartition ? FFileSystemPartition->size : 0);
  TEspSignedArtifactInfo Info = {};
  if( !EspSignedArtifactVerifyPrefix( Prefix, FixedPrefixSize + SignatureSize,
       Part == TPart::Firmware ? TEspSignedArtifactType::Firmware :
         TEspSignedArtifactType::FileSystem,
       ESP_UPDATE_DEVICE_TYPE, ContentLength, MaximumPayloadSize, Info, Error ) )
   {
    SendText( ClientSocket, 400, Error.c_str() );
    return false;
   }

  const bool Result = Part == TPart::Firmware ?
    HandleFirmware( ClientSocket, Info.PayloadSize, Info.PayloadHash ) :
    HandleFileSystem( ClientSocket, Info.PayloadSize, Info.PayloadHash );
  if( Result )
   {
    FUpdateCompleted = true;
    SendText( ClientSocket, 200, "OK" );
   }
  return Result;
 }

bool TEspRescueUpdater::HandleFirmware( int ClientSocket,
  uint32_t PayloadSize, uint8_t const ExpectedHash[32] )
 {
  if( !FMainPartition || PayloadSize > FMainPartition->size )
   {
    SendText( ClientSocket, 500, "Main application partition is missing or too small" );
    return false;
   }

  esp_ota_handle_t OtaHandle = 0;
  if( esp_ota_begin( FMainPartition, PayloadSize, &OtaHandle ) != ESP_OK )
   {
    SendText( ClientSocket, 500, "Could not start firmware update" );
    return false;
   }

  TEspSignedArtifactHash Hash;
  Hash.Begin();
  uint8_t Buffer[1024];
  uint32_t Remaining = PayloadSize;
  while( Remaining )
   {
    const size_t Wanted = Remaining < sizeof( Buffer ) ? Remaining : sizeof( Buffer );
    if( !ReadExact( ClientSocket, Buffer, Wanted ) )
     {
      esp_ota_abort( OtaHandle );
      SendText( ClientSocket, 400, "Firmware payload is incomplete" );
      return false;
     }
    Hash.Add( Buffer, Wanted );
    if( esp_ota_write( OtaHandle, Buffer, Wanted ) != ESP_OK )
     {
      esp_ota_abort( OtaHandle );
      SendText( ClientSocket, 500, "Could not write firmware" );
      return false;
     }
    Remaining -= Wanted;
   }

  if( !Hash.EndAndCompare( ExpectedHash ) )
   {
    esp_ota_abort( OtaHandle );
    SendText( ClientSocket, 400, "Firmware payload hash mismatch" );
    return false;
   }
  if( esp_ota_end( OtaHandle ) != ESP_OK )
   {
    SendText( ClientSocket, 500, "Firmware image is invalid" );
    return false;
   }
  if( !VerifyWrittenPayload(FMainPartition, PayloadSize, ExpectedHash) )
   {
    SendText(ClientSocket, 500, "Firmware flash readback mismatch");
    return false;
   }
  RestoreRescueBoot();
  return true;
 }

bool TEspRescueUpdater::HandleFileSystem( int ClientSocket,
  uint32_t PayloadSize, uint8_t const ExpectedHash[32] )
 {
  if( !FFileSystemPartition || PayloadSize > FFileSystemPartition->size )
   {
    SendText( ClientSocket, 500, "Filesystem partition is missing or too small" );
    return false;
   }

  if( esp_partition_erase_range( FFileSystemPartition, 0,
        FFileSystemPartition->size ) != ESP_OK )
   {
    SendText( ClientSocket, 500, "Could not erase filesystem partition" );
    return false;
   }

  TEspSignedArtifactHash Hash;
  Hash.Begin();
  uint8_t Buffer[1024];
  uint32_t Remaining = PayloadSize;
  size_t Offset = 0;
  while( Remaining )
   {
    const size_t Wanted = Remaining < sizeof( Buffer ) ? Remaining : sizeof( Buffer );
    if( !ReadExact( ClientSocket, Buffer, Wanted ) )
     {
      SendText( ClientSocket, 400, "Filesystem payload is incomplete" );
      return false;
     }
    Hash.Add( Buffer, Wanted );
    if( esp_partition_write( FFileSystemPartition, Offset,
                             Buffer, Wanted ) != ESP_OK )
     {
      SendText( ClientSocket, 500, "Could not write filesystem" );
      return false;
     }
    Offset += Wanted;
    Remaining -= Wanted;
   }
  if( !Hash.EndAndCompare( ExpectedHash ) )
   {
    SendText( ClientSocket, 400, "Filesystem payload hash mismatch" );
    return false;
   }
  if( !VerifyWrittenPayload(FFileSystemPartition, PayloadSize, ExpectedHash) )
   {
    SendText(ClientSocket, 500, "Filesystem flash readback mismatch");
    return false;
   }
  return true;
 }

void TEspRescueUpdater::HandleCommit( int ClientSocket )
 {
  if( !FUpdateCompleted )
   {
    SendText( ClientSocket, 400, "No successful update uploaded" );
    return;
   }
  HandleMain( ClientSocket );
 }

void TEspRescueUpdater::HandleMain( int ClientSocket )
 {
  if( const char * Error = RescueMainError() ) { SendText(ClientSocket, 400, Error); return; }
  if( !FMainPartition )
   {
    SendText( ClientSocket, 500, "Main application partition app0 was not found" );
    return;
   }
  if( esp_ota_set_boot_partition( FMainPartition ) != ESP_OK )
   {
    RestoreRescueBoot();
    SendText( ClientSocket, 500, "Could not select main application for next boot" );
    return;
   }

  SendText( ClientSocket, 200, "Starting main application..." );
  vTaskDelay( pdMS_TO_TICKS( 100 ) );
  shutdown( ClientSocket, SHUT_RDWR );
  close( ClientSocket );
  vTaskDelay( pdMS_TO_TICKS( 200 ) );
  esp_restart();
 }

void TEspRescueUpdater::Loop(void)
 {
  if( FServerSocket < 0 )
    return;

  sockaddr_storage SourceAddress = {};
  socklen_t SourceAddressLength = sizeof( SourceAddress );
  const int ClientSocket = accept( FServerSocket,
    reinterpret_cast<sockaddr *>( &SourceAddress ), &SourceAddressLength );
  if( ClientSocket < 0 )
    return;

  timeval Timeout = {};
  Timeout.tv_sec = HttpTimeoutSeconds;
  setsockopt( ClientSocket, SOL_SOCKET, SO_RCVTIMEO, &Timeout, sizeof( Timeout ) );
  setsockopt( ClientSocket, SOL_SOCKET, SO_SNDTIMEO, &Timeout, sizeof( Timeout ) );

  HandleClient( ClientSocket );
  shutdown( ClientSocket, SHUT_RDWR );
  close( ClientSocket );
 }

bool TEspRescueUpdater::ReadHeaders( int ClientSocket,
  uint32_t & ContentLength )
 {
  char Line[96];
  ContentLength = 0;
  while( true )
   {
    if( !ReadLine( ClientSocket, Line, sizeof( Line ), true ) )
      return false;
    if( !Line[0] )
      return true;

    if( IsContentLengthHeader( Line ) )
     {
      uint32_t Value;
      if( !ParseUInt32( Line + sizeof( "content-length:" ) - 1, Value ) )
        return false;
      ContentLength = Value;
     }
   }
 }

bool TEspRescueUpdater::ReadLine( int ClientSocket, char * Buffer,
  size_t BufferSize, bool DiscardOverflow )
 {
  size_t Length = 0;
  while( true )
   {
    char Ch;
    const int Count = recv( ClientSocket, &Ch, 1, 0 );
    if( Count == 0 )
      return false;
    if( Count < 0 )
     {
      if( errno == EINTR )
        continue;
      return false;
     }
    if( Ch == '\n' )
     {
      if( Length && Buffer[Length - 1] == '\r' )
        --Length;
      Buffer[Length] = 0;
      return true;
     }
    if( Length + 1 >= BufferSize )
     {
      if( !DiscardOverflow )
        return false;
      continue;
     }
    Buffer[Length++] = Ch;
   }
 }

bool TEspRescueUpdater::ReadExact( int ClientSocket, uint8_t * Buffer,
  size_t Size )
 {
  size_t Done = 0;
  while( Done < Size )
   {
    const int Count = recv( ClientSocket, Buffer + Done, Size - Done, 0 );
    if( Count == 0 )
      return false;
    if( Count < 0 )
     {
      if( errno == EINTR )
        continue;
      return false;
     }
    Done += size_t( Count );
   }
  return true;
 }

bool TEspRescueUpdater::SendAll( int ClientSocket, char const * Text )
 {
  return SendAll( ClientSocket, Text, strlen( Text ) );
 }

bool TEspRescueUpdater::SendAll( int ClientSocket, void const * Data,
  size_t Size )
 {
  size_t Done = 0;
  uint8_t const * Bytes = static_cast<uint8_t const *>( Data );
  while( Done < Size )
   {
    const int Count = send( ClientSocket, Bytes + Done, Size - Done, 0 );
    if( Count < 0 )
     {
      if( errno == EINTR )
        continue;
      return false;
     }
    if( Count == 0 )
      return false;
    Done += size_t( Count );
   }
  return true;
 }

void TEspRescueUpdater::RestoreRescueBoot(void)
 {
  if( !RescueGeometryValid() ) return;
  esp_partition_t const * RunningPartition = esp_ota_get_running_partition();
  if( RunningPartition )
    esp_ota_set_boot_partition( RunningPartition );
 }

void TEspRescueUpdater::SendRecoveryPage( int ClientSocket )
 {
  static char const PageStart[] =
    "HTTP/1.1 200 OK\r\n"
    "Connection: close\r\n"
    "Content-Type: text/html; charset=utf-8\r\n\r\n"
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>Rescue</title><style>.f{display:flex;align-items:center;gap:.5em;margin:.8em 0;}.f label{flex:0 0 7em}.f input{flex:1 1 auto;min-width:0;width:100%;box-sizing:border-box}</style></head><body><h1>";
  static char const PageMiddle[] =
    " Rescue</h1><p>Version Rescue ";
  static char const PageEnd[] =
    "</p>"
    "<div class='f'><label for='fw'>Firmware:</label><input id='fw' type='file' accept='.bin_signed'></div>"
    "<div class='f'><label for='fs'>Filesystem:</label><input id='fs' type='file' accept='.littlefs_signed'></div>"
    "<button onclick='go()'>Update</button> "
    "<button onclick='mainApp()'>Start Main</button><p id='s'></p>"
    "<script>"
    "async function up(p,f){let r=await fetch(p,{method:'POST',body:f});"
    "let t=await r.text();if(!r.ok)throw Error(t);}"
    "async function go(){let s=document.getElementById('s'),"
    "f=document.getElementById('fw').files[0],"
    "x=document.getElementById('fs').files[0];"
    "if(!f&&!x){s.textContent='Select firmware and/or filesystem';return;}"
    "try{s.textContent='Updating...';if(f)await up('/Firmware',f);"
    "if(x)await up('/Filesystem',x);"
    "let r=await fetch('/Commit',{method:'POST'}),t=await r.text();"
    "if(!r.ok)throw Error(t);await waitMain(s,Date.now());}"
    "catch(e){s.textContent='Update failed: '+e.message;}}"
    "async function probe(u){let c=new AbortController(),x=setTimeout(()=>c.abort(),1500);"
    "try{return await fetch(u,{cache:'no-store',signal:c.signal});}finally{clearTimeout(x);}}"
    "async function waitMain(s,b){let n=0,r;"
    "while(Date.now()-b<120000){n++;s.textContent='Waiting for Main · Versuch '+n+' · '+Math.floor((Date.now()-b)/1000)+' s · '+(n&1?'●':'○');"
    "try{r=await probe('/api/v1/device?MainProbe='+Date.now());if(r.ok){location.replace('/Index.html?Updated='+Date.now());return;}}catch(e){}"
    "await new Promise(q=>setTimeout(q,750));}"
    "throw Error('Main did not become reachable within 120 seconds');}"
    "async function mainApp(){let s=document.getElementById('s');"
    "try{s.textContent='Starting main application...';"
    "let r=await fetch('/Main',{method:'POST'}),t=await r.text();if(!r.ok)throw Error(t);"
    "await waitMain(s,Date.now());}"
    "catch(e){s.textContent='Start failed: '+e.message;}}"
    "</script></body></html>";

  SendAll( ClientSocket, PageStart );
  SendAll( ClientSocket, FProjectName );
  SendAll( ClientSocket, PageMiddle );
  SendAll( ClientSocket, FRescueVersion );
  SendAll( ClientSocket, PageEnd );
 }

void TEspRescueUpdater::SendText( int ClientSocket, int Status,
  char const * Text )
 {
  SendAll( ClientSocket, StatusLine( Status ) );
  SendAll( ClientSocket,
    "Connection: close\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n" );
  SendAll( ClientSocket, Text );
 }
