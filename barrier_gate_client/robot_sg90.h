#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#include "lwip/sockets.h"
#include "ohos_init.h"
#include "cmsis_os2.h"
#include "oled_ssd1306.h"
#include "robot_sg90.h"  // 添加舵机控制头文件

// 声明在 demo_entry_cmsis.c 中定义的函数
extern void OledShowChinese3(uint8_t x, uint8_t y, uint8_t idx);
extern void show_status(const char* status, int chinese_idx);
extern int control_flag;

// 辅助函数：修剪字符串末尾的空白字符
static void trim_trailing_whitespace(char* str) {
    if (str == NULL) return;

    int len = strlen(str);
    while (len > 0 && isspace((unsigned char)str[len - 1])) {
        str[len - 1] = '\0';
        len--;
    }
}

// 辅助函数：打印字符串的十六进制内容（用于调试）
static void print_hex_debug(const char* label, const char* str) {
    printf("%s: [", label);
    for(int i = 0; i < strlen(str); i++) {
        if(str[i] >= 32 && str[i] <= 126) {
            printf("%c", str[i]);
        } else {
            printf("\\x%02X", (unsigned char)str[i]);
        }
    }
    printf("] (length=%d)\n", strlen(str));
}

void UdpClientTest(const char *host, unsigned short port)
{
    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        printf("Socket create failed!\n");
        return;
    }

    struct sockaddr_in toAddr = {0};
    toAddr.sin_family = AF_INET;
    toAddr.sin_port = htons(port);

    if (inet_pton(AF_INET, host, &toAddr.sin_addr) <= 0) {
        printf("Invalid server address!\n");
        lwip_close(sockfd);
        return;
    }

    // 发送连接消息到服务器
    char request[] = "Barrier_Ready";
    ssize_t retval = sendto(sockfd, request, sizeof(request), 0,
                          (struct sockaddr *)&toAddr, sizeof(toAddr));

    if (retval < 0) {
        printf("Send to server failed!\n");
        lwip_close(sockfd);
        return;
    }

    printf("Connected to server %s:%d\n", host, port);
    show_status("Ready", -1);

    struct sockaddr_in fromAddr = {0};
    socklen_t fromLen = sizeof(fromAddr);
    char response[128] = "";

    while (1) {
        retval = lwip_recvfrom(sockfd, response, sizeof(response)-1, 0,
                              (struct sockaddr *)&fromAddr, &fromLen);

        if (retval > 0) {
            response[retval] = '\0';
            printf("Raw received: ");
            print_hex_debug("Raw received", response);  // 修正参数

            // 修剪可能的换行符
            trim_trailing_whitespace(response);
            printf("After trimming: ");
            print_hex_debug("After trimming", response);  // 修正参数

            int command_processed = 0;

            // 尝试解析新格式：省份代码,车牌号,命令
            char *first_comma = strchr(response, ',');
            if (first_comma != NULL) {
                *first_comma = '\0'; // 分割出省份代码
                char *province_code_str = response;

                char *second_comma = strchr(first_comma + 1, ',');
                if (second_comma != NULL) {
                    *second_comma = '\0'; // 分割出车牌号
                    char *plate_number = first_comma + 1;
                    char *command_str = second_comma + 1;

                    // 修剪命令字符串
                    trim_trailing_whitespace(command_str);

                    printf("Parsed - Province: %s, Plate: %s, Command: ",
                           province_code_str, plate_number);
                    print_hex_debug("Command", command_str);  // 修正参数

                    // 转换省份代码为整数
                    int province_code = atoi(province_code_str);

                    // 在OLED上显示车牌和状态
                    OledFillScreen(0x00);
                    OledShowString(0, 0, "Barrier Gate", FONT8x16);
                    OledShowString(0, 2, "Plate:", FONT8x16);

                    // 显示省份汉字（根据代码）
                    if (province_code >= 0 && province_code <= 33) {
                        OledShowChinese3(40, 2, province_code);
                        printf("Display province with code: %d\n", province_code);
                    } else {
                        OledShowString(40, 2, "??", FONT8x16);
                        printf("Invalid province code: %d\n", province_code);
                    }

                    // 显示车牌剩余部分
                    OledShowString(56, 2, plate_number, FONT8x16);

                    // 根据命令控制舵机 - 使用直接比较和已验证的逻辑
                    if (strcmp(command_str, "1") == 0 ||
                        strcmp(command_str, "close") == 0 ||
                        command_str[0] == '1') {
                        printf("=== CLOSE COMMAND DETECTED ===\n");
                        // 复用已验证的close逻辑
                        engine_turn_right();
                        control_flag = 0;
                        OledShowString(0, 4, "Status: CLOSE", FONT8x16);
                        command_processed = 1;
                    }
                    else if (strcmp(command_str, "0") == 0 ||
                             strcmp(command_str, "open") == 0 ||
                             command_str[0] == '0') {
                        printf("=== OPEN COMMAND DETECTED ===\n");
                        // 复用已验证的open逻辑
                        engine_turn_left();
                        control_flag = 1;
                        OledShowString(0, 4, "Status: OPEN", FONT8x16);
                        command_processed = 1;
                    }
                    else if (strcmp(command_str, "2") == 0 ||
                             strcmp(command_str, "stop") == 0 ||
                             command_str[0] == '2') {
                        printf("=== STOP COMMAND DETECTED ===\n");
                        // 复用已验证的stop逻辑
                        regress_middle();
                        OledShowString(0, 4, "Status: STOP", FONT8x16);
                        command_processed = 1;
                    }
                    else {
                        printf("Unknown command in new format: %s\n", command_str);
                        OledShowString(0, 4, "Status: ERROR", FONT8x16);
                        command_processed = 1;
                    }
                }
            }

            // 如果没有处理新格式，尝试旧格式的文本命令
            if (!command_processed) {
                printf("Trying old format parsing...\n");

                // 兼容旧格式的文本命令
                if (strstr(response, "open") != NULL) {
                    printf("=== OPEN TEXT COMMAND DETECTED ===\n");
                    engine_turn_left();
                    control_flag = 1;
                    show_status("OPEN", 0);
                }
                else if (strstr(response, "close") != NULL) {
                    printf("=== CLOSE TEXT COMMAND DETECTED ===\n");
                    engine_turn_right();
                    control_flag = 0;
                    show_status("CLOSE", 1);
                }
                else if (strstr(response, "stop") != NULL) {
                    printf("=== STOP TEXT COMMAND DETECTED ===\n");
                    regress_middle();
                    show_status("STOP", -1);
                }
                else {
                    printf("Unknown command format: %s\n", response);
                    OledShowString(0, 4, "Status: UNKNOWN", FONT8x16);
                }
            }
        } else {
            osDelay(100);
        }
        osDelay(100);
    }
    lwip_close(sockfd);
}