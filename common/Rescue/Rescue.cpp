// Rescue.cpp, Version: 2.19
#include <Arduino.h>
#include "RescueGuard.h"
#include <cstring>

#include <esp_event.h>
#include <esp_netif.h>
#include <esp_timer.h>
#include <esp_wifi.h>
#include <esp_wifi_default.h>
#include <nvs.h>
#include <nvs_flash.h>

#include "EspRescueProject.h"
#include "EspRescueHardware.h"
#include "EspRescueUpdater.h"

namespace
 {
  constexpr uint32_t StaRetryMs = 10000;
  constexpr char RescueNvsNamespace[] = "AqRescue";
  constexpr char RescueWlanKey[] = "Wlan";
  constexpr uint32_t StatusLedUnitMs = 10;
  constexpr uint8_t StatusLedSosUnits[] =
   {
    10, 20, 10, 20, 10, 40,
    30, 20, 30, 20, 30, 40,
    10, 20, 10, 20, 10, 90
   };
  constexpr uint8_t StatusLedRepeatOffUnitsConnected = 150;

  TEspRescueUpdater RescueUpdater;
  uint8_t NextWlanIndex = 0;
  uint32_t NextStationRetryMs = 0;
  uint32_t NextStatusLedToggleMs = 0;
  uint8_t StatusLedSosPhase = 0;
  bool StaHasIp = false;

  bool StationConnected(void);

  uint32_t NowMs(void)
   {
    return uint32_t( esp_timer_get_time() / 1000ULL );
   }

  uint8_t StatusLedPhaseUnits(void)
   {
    constexpr uint8_t LastPhase =
      uint8_t( sizeof( StatusLedSosUnits ) / sizeof( StatusLedSosUnits[0] ) - 1 );
    if( StatusLedSosPhase == LastPhase && StaHasIp )
      return StatusLedRepeatOffUnitsConnected;
    return StatusLedSosUnits[StatusLedSosPhase];
   }

  void SetStatusLedPhase(void)
   {
    const int Level = ( StatusLedSosPhase & 1 ) == 0 ?
      EspRescueHardware::StatusLedActiveLevel : !EspRescueHardware::StatusLedActiveLevel;
    digitalWrite( EspRescueHardware::StatusLedPin, Level );
    NextStatusLedToggleMs = NowMs() +
      uint32_t( StatusLedPhaseUnits() ) * StatusLedUnitMs;
   }

  void SetupHardware(void)
   {
    if( !RescueGeometryValid() ) return;
    if( EspRescueHardware::KeyPin >= 0 )
      pinMode( EspRescueHardware::KeyPin, INPUT_PULLUP );

    if( EspRescueHardware::StatusLedPin >= 0 )
     {
      StatusLedSosPhase = 0;
      SetStatusLedPhase();
      pinMode( EspRescueHardware::StatusLedPin, OUTPUT );
     }
   }

  void UpdateStatusLed(void)
   {
    if( EspRescueHardware::StatusLedPin < 0 || !RescueGeometryValid() )
      return;

    const uint32_t Now = NowMs();
    if( int32_t( Now - NextStatusLedToggleMs ) < 0 )
      return;

    StatusLedSosPhase = uint8_t( (StatusLedSosPhase + 1) %
      (sizeof( StatusLedSosUnits ) / sizeof( StatusLedSosUnits[0] )) );
    SetStatusLedPhase();
   }

  bool SetStationConfig( char const * Ssid, char const * Password )
   {
    wifi_config_t Config = {};
    const size_t SsidLen = strlen( Ssid );
    if( !SsidLen || SsidLen >= sizeof( Config.sta.ssid ) )
      return false;

    memcpy( Config.sta.ssid, Ssid, SsidLen );
    if( Password )
     {
      const size_t PasswordLen = strlen( Password );
      if( PasswordLen >= sizeof( Config.sta.password ) )
        return false;
      memcpy( Config.sta.password, Password, PasswordLen );
     }

    esp_wifi_disconnect();

    esp_err_t Error = ESP_ERR_WIFI_STATE;
    for( uint8_t Try = 0; Try < 10 && Error == ESP_ERR_WIFI_STATE; ++Try )
     {
      if( Try )
        delay( 50 );
      Error = esp_wifi_set_config( WIFI_IF_STA, &Config );
     }
    if( Error != ESP_OK )
      return false;

    Error = ESP_ERR_WIFI_CONN;
    for( uint8_t Try = 0; Try < 10 && Error == ESP_ERR_WIFI_CONN; ++Try )
     {
      if( Try )
        delay( 50 );
      Error = esp_wifi_connect();
     }
    return Error == ESP_OK;
   }

  void StartNextStation(void)
   {
    for( uint8_t Try = 0; Try < 2; ++Try )
     {
      const uint8_t Index = NextWlanIndex;

      char const * Ssid = Index ? ESP_RESCUE_WLAN_SSID2 : ESP_RESCUE_WLAN_SSID;
      char const * Password = Index ? ESP_RESCUE_WLAN_PW2 : ESP_RESCUE_WLAN_PW;
      if( !Ssid[0] )
       {
        NextWlanIndex = 1 - Index;
        continue;
       }

      if( SetStationConfig( Ssid, Password ) )
       {
        NextWlanIndex = 1 - Index;
        NextStationRetryMs = NowMs() + StaRetryMs;
       }
       else
       {
        NextWlanIndex = Index;
        NextStationRetryMs = NowMs() + 250;
       }
      return;
     }

    NextStationRetryMs = NowMs() + StaRetryMs;
   }

  void WifiEventHandler( void *, esp_event_base_t EventBase,
    int32_t EventId, void * )
   {
    if( EventBase == IP_EVENT && EventId == IP_EVENT_STA_GOT_IP )
      StaHasIp = true;
    else if( EventBase == WIFI_EVENT && EventId == WIFI_EVENT_STA_DISCONNECTED )
      StaHasIp = false;
   }

  uint8_t LoadPreferredWlanIndex(void)
   {
    if( nvs_flash_init() != ESP_OK )
      return 0;

    nvs_handle_t Handle;
    if( nvs_open( RescueNvsNamespace, NVS_READONLY, &Handle ) != ESP_OK )
      return 0;

    uint8_t Index = 0;
    const esp_err_t Error = nvs_get_u8( Handle, RescueWlanKey, &Index );
    nvs_close( Handle );
    return Error == ESP_OK && Index <= 1 ? Index : 0;
   }

  bool SetupWifi(void)
   {
    esp_err_t Error = esp_netif_init();
    if( Error != ESP_OK && Error != ESP_ERR_INVALID_STATE )
      return false;

    Error = esp_event_loop_create_default();
    if( Error != ESP_OK && Error != ESP_ERR_INVALID_STATE )
      return false;

    if( esp_event_handler_register( IP_EVENT, IP_EVENT_STA_GOT_IP,
      &WifiEventHandler, nullptr ) != ESP_OK )
      return false;
    if( esp_event_handler_register( WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED,
      &WifiEventHandler, nullptr ) != ESP_OK )
      return false;

    esp_netif_t * StaNetif = esp_netif_create_default_wifi_sta();
    esp_netif_t * ApNetif = esp_netif_create_default_wifi_ap();
    if( !StaNetif || !ApNetif )
      return false;

    esp_netif_set_hostname( StaNetif, ESP_RESCUE_PROJECT_NAME );

    wifi_init_config_t InitConfig = WIFI_INIT_CONFIG_DEFAULT();
    if( esp_wifi_init( &InitConfig ) != ESP_OK )
      return false;
    if( esp_wifi_set_storage( WIFI_STORAGE_RAM ) != ESP_OK )
      return false;
    if( esp_wifi_set_mode( WIFI_MODE_APSTA ) != ESP_OK )
      return false;

    wifi_config_t ApConfig = {};
    char ApSsid[sizeof( ApConfig.ap.ssid ) + 1] = {};
    size_t Length = strlen( ESP_RESCUE_PROJECT_NAME );
    const size_t MaxLength = sizeof( ApConfig.ap.ssid ) - sizeof( "-Rescue" );
    if( Length > MaxLength ) Length = MaxLength;
    memcpy( ApSsid, ESP_RESCUE_PROJECT_NAME, Length );
    constexpr char Suffix[] = "-Rescue";
    memcpy( ApSsid + Length, Suffix, sizeof( Suffix ) );
    Length += sizeof( Suffix ) - 1;
    memcpy( ApConfig.ap.ssid, ApSsid, Length );
    ApConfig.ap.ssid_len = Length;
    ApConfig.ap.channel = 1;
    ApConfig.ap.max_connection = 4;
    ApConfig.ap.authmode = WIFI_AUTH_OPEN;
    if( esp_wifi_set_config( WIFI_IF_AP, &ApConfig ) != ESP_OK )
      return false;

    if( esp_wifi_start() != ESP_OK )
      return false;

    NextWlanIndex = LoadPreferredWlanIndex();
    StartNextStation();
    return true;
   }

  bool StationConnected(void)
   {
    return StaHasIp;
   }
 }

void setup(void)
 {
  SetupHardware();
  if( SetupWifi() )
    RescueUpdater.Setup( ESP_RESCUE_PROJECT_NAME, ESP_RESCUE_VERSION );
 }

void loop(void)
 {
  UpdateStatusLed();
  RescueUpdater.Loop();

  if( StationConnected() )
    return;

  if( int32_t( NowMs() - NextStationRetryMs ) >= 0 )
    StartNextStation();
 }
