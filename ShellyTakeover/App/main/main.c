// main.c, Version: 1.00
#include "Platform.h"
#include "esp_http_server.h"
#include "esp_system.h"
#include "esp_mac.h"
#include "cJSON.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include <stdio.h>
#include <string.h>
void TakeoverNetworkStart(void);
bool TakeoverNetworkReady(void);
void TakeoverNetworkRetry(void);
static portMUX_TYPE Lock=portMUX_INITIALIZER_UNLOCKED;
static TTakeoverResult Result={.Phase=TakeoverWaiting,.DoNotRestart=true};
static void PhaseChanged(TTakeoverPhase Phase)
 {
  // Publish failure together with its error and rollback status in app_main.
  if(Phase==TakeoverFailed) return;
  portENTER_CRITICAL(&Lock);Result.Phase=Phase;portEXIT_CRITICAL(&Lock);
 }
static char * StatusText(const TTakeoverResult * Snapshot)
 {
  cJSON * Json=cJSON_CreateObject(); if(!Json) return NULL;
  cJSON_AddStringToObject(Json,"Application","ShellyTakeover");
  uint8_t Mac[6];
  if(esp_read_mac(Mac,ESP_MAC_WIFI_STA)==ESP_OK)
   {
    char Address[13];
    snprintf(Address,sizeof(Address),"%02X%02X%02X%02X%02X%02X",Mac[0],Mac[1],Mac[2],Mac[3],Mac[4],Mac[5]);
    cJSON_AddStringToObject(Json,"Mac",Address);
   }
  cJSON_AddStringToObject(Json,"Phase",TakeoverPhaseName(Snapshot->Phase));
  cJSON_AddStringToObject(Json,"Error",Snapshot->Error);
  cJSON_AddBoolToObject(Json,"RescueReady",Snapshot->RescueReady);
  cJSON_AddBoolToObject(Json,"RollbackVerified",Snapshot->RollbackVerified);
  cJSON_AddBoolToObject(Json,"DoNotRestart",Snapshot->DoNotRestart);
  char * Text=cJSON_PrintUnformatted(Json);cJSON_Delete(Json);
  return Text;
 }
static void BroadcastFailure(const TTakeoverResult * Snapshot)
 {
  char * Text=StatusText(Snapshot);
  if(!Text) return;
  int Socket=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
  if(Socket>=0)
   {
    int On=1;
    struct sockaddr_in Destination={.sin_family=AF_INET,.sin_port=htons(45678),.sin_addr.s_addr=INADDR_BROADCAST};
    if(setsockopt(Socket,SOL_SOCKET,SO_BROADCAST,&On,sizeof(On))==0)
      for(unsigned Attempt=0;Attempt<3;Attempt++)
       {
        sendto(Socket,Text,strlen(Text),0,(struct sockaddr *)&Destination,sizeof(Destination));
        vTaskDelay(pdMS_TO_TICKS(250));
       }
    close(Socket);
   }
  cJSON_free(Text);
 }
static esp_err_t Status(httpd_req_t * Request)
 {
  TTakeoverResult Snapshot;
  portENTER_CRITICAL(&Lock);Snapshot=Result;portEXIT_CRITICAL(&Lock);
  char * Text=StatusText(&Snapshot);if(!Text) return ESP_ERR_NO_MEM;
  httpd_resp_set_type(Request,"application/json");httpd_resp_set_hdr(Request,"Cache-Control","no-store");
  esp_err_t Sent=httpd_resp_sendstr(Request,Text);cJSON_free(Text);return Sent;
 }
static esp_err_t Page(httpd_req_t * Request)
 {
  httpd_resp_set_type(Request,"text/html");
  return httpd_resp_sendstr(Request,"<!doctype html><html lang=de><meta charset=utf-8><title>ShellyTakeover</title><h1>ShellyTakeover</h1><p>Die Übernahme läuft automatisch. Bei Fehlern bleibt diese Diagnose erreichbar.</p><pre id=status></pre><script>async function poll(){try{const r=await fetch('/status',{cache:'no-store'});document.getElementById('status').textContent=JSON.stringify(await r.json(),null,2)}catch(e){document.getElementById('status').textContent='Verbindung unterbrochen; Rescue wird gestartet oder Gerät nicht erreichbar.'}setTimeout(poll,2000)}poll()</script></html>");
 }
void app_main(void)
 {
  TakeoverNetworkStart();
  httpd_config_t Config=HTTPD_DEFAULT_CONFIG();Config.stack_size=8192;Config.lru_purge_enable=true;
  httpd_handle_t Server;ESP_ERROR_CHECK(httpd_start(&Server,&Config));
  httpd_uri_t Root={.uri="/",.method=HTTP_GET,.handler=Page};httpd_uri_t State={.uri="/status",.method=HTTP_GET,.handler=Status};
  ESP_ERROR_CHECK(httpd_register_uri_handler(Server,&Root));ESP_ERROR_CHECK(httpd_register_uri_handler(Server,&State));
  // HTTP is ready before any hardware or migration guard; wait for a LAN address.
  unsigned Seconds=0;
  while(!TakeoverNetworkReady()) {vTaskDelay(pdMS_TO_TICKS(1000));if(++Seconds%15==0) TakeoverNetworkRetry();}
  TTakeoverOps Ops=*ShellyTakeoverOperations();Ops.PhaseChanged=PhaseChanged;
  TTakeoverResult Finished=TakeoverRun(&Ops);
  if(Finished.Phase==TakeoverFailed)
    Finished.DoNotRestart=!ShellyReturnToStock();
  portENTER_CRITICAL(&Lock);Result=Finished;portEXIT_CRITICAL(&Lock);
  if(Finished.Phase==TakeoverFailed) BroadcastFailure(&Finished);
  if(!Finished.DoNotRestart) {vTaskDelay(pdMS_TO_TICKS(5000));esp_restart();}
  for(;;) {vTaskDelay(pdMS_TO_TICKS(15000));TakeoverNetworkRetry();}
 }
