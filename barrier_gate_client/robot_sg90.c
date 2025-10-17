#include <stdio.h>
#include <stdlib.h>
#include <memory.h>

#include "ohos_init.h"
#include "cmsis_os2.h"
#include "iot_gpio.h"
#include "hi_io.h"
#include "hi_time.h"

//查阅机器人板原理图可知，SG90舵机通过GPIO2与3861连接
//SG90舵机的控制需要MCU产生一个周期为20ms的脉冲信号，以0.5ms到2.5ms的高电平来控制舵机转动的角度
#define GPIO2 2

//输出20000微秒的脉冲信号(x微秒高电平,20000-x微秒低电平)
void set_angle( unsigned int duty) {
    IoTGpioSetDir(GPIO2, IOT_GPIO_DIR_OUT);//设置GPIO2为输出模式

    //GPIO2输出x微秒高电平
    IoTGpioSetOutputVal(GPIO2, IOT_GPIO_VALUE1);
    hi_udelay(duty);

    //GPIO2输出20000-x微秒低电平
    IoTGpioSetOutputVal(GPIO2, IOT_GPIO_VALUE0);
    hi_udelay(20000 - duty);
}

/*Steering gear turn left
1、依据角度与脉冲的关系，设置高电平时间为1000微秒
2、发送10次脉冲信号，控制舵机向左旋转45度
*/
void engine_turn_left(void)
{
    for (int i = 0; i <10; i++) {
        set_angle(1000);
    }
}

/*Steering gear turn right
1、依据角度与脉冲的关系，设置高电平时间为2000微秒
2、发送10次脉冲信号，控制舵机向右旋转45度
*/
void engine_turn_right(void)
{
    for (int i = 0; i <10; i++) {
        set_angle(2000);
    }
}

/*Steering gear return to middle
1、依据角度与脉冲的关系，设置高电平时间为1500微秒
2、发送10次脉冲信号，控制舵机居中
*/
void regress_middle(void)
{
    for (int i = 0; i <10; i++) {
        set_angle(1500);
    }
}

/*Gate Open - 路障打开
1、设置高电平时间为2000微秒，舵机向右旋转
2、发送20次脉冲信号，确保路障完全打开
3、适用于授权通过的情况
*/
void GateOpen(void)
{
    printf("Opening gate...\r\n");
    for (int i = 0; i < 20; i++) {
        set_angle(2000);  // 右转，打开路障
    }
    printf("Gate opened successfully!\r\n");
}

/*Gate Close - 路障关闭
1、设置高电平时间为1000微秒，舵机向左旋转
2、发送20次脉冲信号，确保路障完全关闭
3、适用于未授权的情况
*/
void GateClose(void)
{
    printf("Closing gate...\r\n");
    for (int i = 0; i < 20; i++) {
        set_angle(1000);  // 左转，关闭路障
    }
    printf("Gate closed successfully!\r\n");
}