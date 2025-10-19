#include <stdio.h>
#include <stdlib.h>
#include <memory.h>

#include "ohos_init.h"
#include "cmsis_os2.h"
#include "iot_gpio.h"
#include "hi_io.h"
#include "hi_time.h"

// SG90舵机通过GPIO2连接
#define GPIO2 2

// 全局变量，避免重复初始化
static int servo_initialized = 0;

// 初始化GPIO
void servo_init(void) {
    if (!servo_initialized) {
        IoTGpioInit(GPIO2);
        hi_io_set_func(GPIO2, 0); // GPIO功能
        IoTGpioSetDir(GPIO2, IOT_GPIO_DIR_OUT);
        servo_initialized = 1;
        printf("Servo initialized\n");
    }
}

// 输出PWM信号控制舵机角度
void set_angle(unsigned int duty) {
    // GPIO2输出高电平
    IoTGpioSetOutputVal(GPIO2, IOT_GPIO_VALUE1);
    hi_udelay(duty);

    // GPIO2输出低电平
    IoTGpioSetOutputVal(GPIO2, IOT_GPIO_VALUE0);
    hi_udelay(20000 - duty);
}

/* 舵机向左转 - 抬起闸机 */
void engine_turn_left(void)
{
    servo_init();
    printf("Turning left - Barrier UP\n");
    for (int i = 0; i < 200; i++) {  // 增加循环次数
        set_angle(500);  // 0.5ms 高电平
    }
}

/* 舵机向右转 - 放下闸机 */
void engine_turn_right(void)
{
    servo_init();
    printf("Turning right - Barrier DOWN\n");
    for (int i = 0; i < 200; i++) {  // 增加循环次数
        set_angle(2500); // 2.5ms 高电平
    }
}

/* 舵机回中 - 停止位置 */
void regress_middle(void)
{
    servo_init();
    printf("Returning to middle\n");
    for (int i = 0; i < 200; i++) {  // 增加循环次数
        set_angle(1500); // 1.5ms 高电平
    }
}