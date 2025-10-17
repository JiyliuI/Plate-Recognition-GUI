#include <stdio.h>          // 标准输入输出
#include <unistd.h>         // POSIX标准接口
#include <errno.h>          // 错误码
#include <string.h>         // 字符串处理(操作字符数组)
#include <stdint.h>         // 用于 uint8_t

#include "lwip/sockets.h"   // lwIP TCP/IP协议栈：Socket API
#include "ohos_init.h"      // 用于初始化服务(services)和功能(features)
#include "cmsis_os2.h"      // CMSIS-RTOS API V2
#include "oled_ssd1306.h"
#include "robot_sg90.h"     // **[新增] 假设舵机控制接口在此头文件中**


#define MAX_PLATE_CHARS_NO_CN 7 // 剩余车牌号的最大长度
// 协议: 1字节汉字索引 + 7字节 ASCII + 1字节状态索引 = 9 字节
#define CAR_DATA_LEN (1 + MAX_PLATE_CHARS_NO_CN + 1)

// **[新增] 状态索引宏 (需与 Python Server 中的 CHINESE_PLATE_MAPPING 保持一致)**
#define STATUS_DENY 31  // '禁' 的索引
#define STATUS_ALLOW 32 // '通' 的索引
#define ACTION_GATE 33  // '行' 的索引

// 用于接收非车牌数据时的缓冲区大小 (假设为 128)
#define BUFFER_SIZE 128


extern int control_flag ;

// 定义接收数据的结构体 (用于解析原始字节)
typedef struct {
    uint8_t chinese_index;     // 汉字索引 (1字节)
    // 增加一个额外的字节用于字符串终止符 '\0'
    char rest_plate[MAX_PLATE_CHARS_NO_CN + 1];
    uint8_t status_index;      // 状态索引 (1字节)
} PlateData_t;


static unsigned char response_buffer[BUFFER_SIZE]; // 用于接收原始字节 (使用 BUFFER_SIZE，最大可接收 128)
// 要发送的数据（连接请求/心跳）
static char request[] = "connecting";

// 接收缓冲区 (不再直接用于 lwip_recvfrom，而是用于存储解析结果)
// static PlateData_t received_data; // 此变量可以删除

// **[新增] 假设您在 robot_sg90.h 中声明了这两个函数**
extern void GateOpen(void);
extern void GateClose(void);

/// @brief UDP客户端测试函数
/// @param host UDP服务端IP地址
/// @param port UDP服务端端口
void UdpClientTest(const char *host, unsigned short port)
{
    // ... (初始化 socket 和发送第一次连接请求的代码不变)

    // 用于记录发送方的地址信息(IP地址和端口号)
    struct sockaddr_in fromAddr = {0};

    // 用于记录发送方的地址信息长度
    socklen_t fromLen = sizeof(fromAddr);

    // 循环收发数据，模拟长连接
    while (1)
    {
        // 1. **[发送心跳]** 向服务器发送连接/心跳请求
        retval = lwip_sendto(sockfd, request, strlen(request), 0, (struct sockaddr *)&toAddr, sizeof(toAddr));
        if (retval < 0) {
            printf("sendto failed, %ld, %d!\\r\\n", retval, errno);
            break; // 发送失败，退出循环
        }

        // 2. **[接收数据]** 尝试接收服务器的车牌数据包 (9 字节)
        // 使用原始缓冲区 response_buffer 接收数据
        // 注意：此处接收长度为 BUFFER_SIZE，用于兼容 ACK 等非车牌消息
        retval = lwip_recvfrom(sockfd, response_buffer, BUFFER_SIZE, 0, (struct sockaddr *)&fromAddr, &fromLen);

        // 检查接收结果
        if (retval == CAR_DATA_LEN)
        {
            // **[核心逻辑] 接收到完整的 9 字节车牌数据包**
            PlateData_t current_plate; // 使用局部变量存储解析结果

            // 1. 解析汉字索引 (1字节: response_buffer[0])
            current_plate.chinese_index = response_buffer[0];

            // 2. 解析剩余车牌号 (7字节: response_buffer[1] 到 response_buffer[7])
            memcpy(current_plate.rest_plate, &response_buffer[1], MAX_PLATE_CHARS_NO_CN);
            // 确保 ASCII 字符串以 '\0' 结尾 (防止打印乱码)
            current_plate.rest_plate[MAX_PLATE_CHARS_NO_CN] = '\0';

            // 3. 解析状态索引 (1字节: response_buffer[8])
            current_plate.status_index = response_buffer[8];

            // 清屏
            OledFillScreen(0x00);

            // ==========================================================
            // [OLED 显示]
            // ==========================================================
            // Page 0 (第一行): 显示车牌号
            OledShowCNChar(0, 0, current_plate.chinese_index);
            OledShowString(18, 0, current_plate.rest_plate, FONT8x16);

            // Page 2 (第二行): 显示状态和动作
            uint8_t status_x = 0;

            // 1. 显示 '通' (32) 或 '禁' (31)
            OledShowCNChar(status_x, 2, current_plate.status_index);
            status_x += 18;

            // 2. 显示 '行' (33)
            OledShowCNChar(status_x, 2, ACTION_GATE); // 总是显示 '行'

            // 打印日志
            printf("Received Plate: CN Index %d, Rest: %s, Status Index: %d (Status: %s)\\r\\n",
                   current_plate.chinese_index, current_plate.rest_plate,
                   current_plate.status_index,
                   (current_plate.status_index == STATUS_ALLOW ? "ALLOW" : "DENY"));

            // ==========================================================
            // [舵机控制逻辑]
            // ==========================================================
            if (current_plate.status_index == STATUS_ALLOW) // 索引 32: '通' 行
            {
                // GateOpen() 需要在 robot_sg90.c 中实现
                GateOpen();
                printf("Access Granted! Gate Opening.\\r\\n");
            }
            else if (current_plate.status_index == STATUS_DENY) // 索引 31: '禁' 行
            {
                // GateClose() 需要在 robot_sg90.c 中实现
                GateClose();
                printf("Access Denied! Gate remains Closed.\\r\\n");
            }

            // 3. **[反馈]** 发送确认消息给服务器
            char ack_msg[64];
            snprintf(ack_msg, sizeof(ack_msg), "ACK:DISPLAYED:%s", current_plate.rest_plate);
            lwip_sendto(sockfd, ack_msg, strlen(ack_msg), 0, (struct sockaddr *)&fromAddr, fromLen);

        }
        else if (retval > 0)
        {
             // 接收到 ACK 或其他非车牌数据
             // 确保缓冲区中的数据以 '\0' 结尾
             response_buffer[retval] = '\0';
             printf("Received Non-Plate Msg: %s\\r\\n", response_buffer);
        }
        else if (retval < 0)
        {
            printf("recvfrom failed, %ld, %d!\\r\\n", retval, errno);
            break; // 接收失败，退出循环
        }

        // 暂停一段时间，控制通信频率 (例如 100ms)
        osDelay(10);
    }

    // 退出循环后关闭 socket
    lwip_close(sockfd);
    OledFillScreen(0x00);
    OledShowString(0, 0, "Client Disconnected", FONT8x16);
    return;
}