#ifndef WIFI_CONNECTER_H
#define WIFI_CONNECTER_H

#include "wifi_device.h"   // Wi-Fi设备接口：station模式

int ConnectToHotspot(WifiDeviceConfig* apConfig);

void DisconnectWithHotspot(int netId);

#endif  // WIFI_CONNECTER_H