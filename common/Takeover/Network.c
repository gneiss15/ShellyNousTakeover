// Network.c, Version: 1.00
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "EspRescueProject.h"
#include <string.h>
static esp_netif_t * Station;
static unsigned Profile;
static const char * Names[]={ESP_RESCUE_WLAN_SSID,ESP_RESCUE_WLAN_SSID2};
static const char * Passwords[]={ESP_RESCUE_WLAN_PW,ESP_RESCUE_WLAN_PW2};
static void Connect(void)
 {
  wifi_config_t Config={0};
  memcpy(Config.sta.ssid,Names[Profile],strlen(Names[Profile]));
  memcpy(Config.sta.password,Passwords[Profile],strlen(Passwords[Profile]));
  esp_wifi_disconnect();
  if(esp_wifi_set_config(WIFI_IF_STA,&Config)==ESP_OK) esp_wifi_connect();
  memset(&Config,0,sizeof(Config));
 }
void TakeoverNetworkStart(void)
 {
  ESP_ERROR_CHECK(esp_netif_init());ESP_ERROR_CHECK(esp_event_loop_create_default());
  Station=esp_netif_create_default_wifi_sta();
  esp_netif_t * Ap=esp_netif_create_default_wifi_ap();
  ESP_ERROR_CHECK(Station&&Ap?ESP_OK:ESP_FAIL);
  wifi_init_config_t Init=WIFI_INIT_CONFIG_DEFAULT();ESP_ERROR_CHECK(esp_wifi_init(&Init));
  ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
  wifi_config_t Config={0};
  size_t Length=strlen(ESP_RESCUE_PROJECT_NAME); if(Length>31) Length=31;
  memcpy(Config.ap.ssid,ESP_RESCUE_PROJECT_NAME,Length);Config.ap.ssid_len=Length;
  Config.ap.channel=1;Config.ap.max_connection=2;Config.ap.authmode=WIFI_AUTH_OPEN;
  ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP,&Config));ESP_ERROR_CHECK(esp_wifi_start());
  Connect();
 }
bool TakeoverNetworkReady(void)
 {
  esp_netif_ip_info_t Ip={0};
  return Station&&esp_netif_get_ip_info(Station,&Ip)==ESP_OK&&Ip.ip.addr!=0;
 }
void TakeoverNetworkRetry(void)
 {
  if(!TakeoverNetworkReady()) { if(Names[1][0]) Profile=1-Profile;Connect(); }
 }
