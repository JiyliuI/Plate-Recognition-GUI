#include "cmsis_os2.h"      // CMSIS-RTOS API V2
#include "wifi_device.h"    // Wi-Fi设备接口：station模式

#include "lwip/netifapi.h"  // lwIP TCP/IP协议栈：网络接口API
#include "lwip/api_shell.h" // lwIP TCP/IP协议栈：SHELL命令API

static void PrintLinkedInfo(WifiLinkedInfo* info)
{
    if (!info) return;

    static char macAddress[32] = {0};
    unsigned char* mac = info->bssid;
    snprintf(macAddress, sizeof(macAddress), "%02X:%02X:%02X:%02X:%02X:%02X",
        mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    printf("bssid: %s, rssi: %d, connState: %d, reason: %d, ssid: %s\r\n",
        macAddress, info->rssi, info->connState, info->disconnectedReason, info->ssid);
}

static volatile int g_connected = 0;

static void OnWifiConnectionChanged(int state, WifiLinkedInfo* info)
{
    if (!info) return;

    printf("%s %d, state = %d, info = \r\n", __FUNCTION__, __LINE__, state);
    PrintLinkedInfo(info);

    if (state == WIFI_STATE_AVALIABLE) {
        g_connected = 1;
    } else {
        g_connected = 0;
    }
}

static void OnWifiScanStateChanged(int state, int size)
{
    printf("%s %d, state = %X, size = %d\r\n", __FUNCTION__, __LINE__, state, size);
}

static WifiEvent g_defaultWifiEventListener = {
    .OnWifiConnectionChanged = OnWifiConnectionChanged,
    .OnWifiScanStateChanged = OnWifiScanStateChanged
};

static struct netif* g_iface = NULL;

err_t netifapi_set_hostname(struct netif *netif, char *hostname, u8_t namelen);

int ConnectToHotspot(WifiDeviceConfig* apConfig)
{
    WifiErrorCode errCode;
    int netId = -1;

    errCode = RegisterWifiEvent(&g_defaultWifiEventListener);
    printf("RegisterWifiEvent: %d\r\n", errCode);

    errCode = EnableWifi();
    printf("EnableWifi: %d\r\n", errCode);

    errCode = AddDeviceConfig(apConfig, &netId);
    printf("AddDeviceConfig: %d\r\n", errCode);
    
    g_connected = 0;
    errCode = ConnectTo(netId);
    printf("ConnectTo(%d): %d\r\n", netId, errCode);

    while (!g_connected) { // wait until connect to AP
        // printf("connecting\n");
        osDelay(10);
    }
    printf("g_connected: %d\r\n", g_connected);

    g_iface = netifapi_netif_find("wlan0");
    if (g_iface) {
        err_t ret = 0;
        char* hostname = "hispark";
        ret = netifapi_set_hostname(g_iface, hostname, strlen(hostname));
        printf("netifapi_set_hostname: %d\r\n", ret);

        ret = netifapi_dhcp_start(g_iface);
        printf("netifapi_dhcp_start: %d\r\n", ret);

        osDelay(100); // wait DHCP server give me IP 
#if 0
        ret = netifapi_netif_common(g_iface, dhcp_clients_info_show, NULL);
        printf("netifapi_netif_common: %d\r\n", ret);
#else
        // 下面这种方式也可以打印 IP、网关、子网掩码信息
        ip4_addr_t ip = {0};
        ip4_addr_t netmask = {0};
        ip4_addr_t gw = {0};
        ret = netifapi_netif_get_addr(g_iface, &ip, &netmask, &gw);
        if (ret == ERR_OK) {
            printf("ip = %s\r\n", ip4addr_ntoa(&ip));
            printf("netmask = %s\r\n", ip4addr_ntoa(&netmask));
            printf("gw = %s\r\n", ip4addr_ntoa(&gw));
        }
        printf("netifapi_netif_get_addr: %d\r\n", ret);
#endif
    }
    return netId;
}

void DisconnectWithHotspot(int netId)
{
    if (g_iface) {
        err_t ret = netifapi_dhcp_stop(g_iface);
        printf("netifapi_dhcp_stop: %d\r\n", ret);
    }

    WifiErrorCode errCode = Disconnect(); // disconnect with your AP
    printf("Disconnect: %d\r\n", errCode);

    errCode = UnRegisterWifiEvent(&g_defaultWifiEventListener);
    printf("UnRegisterWifiEvent: %d\r\n", errCode);

    RemoveDevice(netId); // remove AP config
    printf("RemoveDevice: %d\r\n", errCode);

    errCode = DisableWifi();
    printf("DisableWifi: %d\r\n", errCode);
}
