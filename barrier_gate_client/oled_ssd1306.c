// OLED显示屏简化版驱动源文件

#include <stdio.h>      // 标准输入输出
#include <stddef.h>     // 标准类型定义

#include "iot_gpio.h"  // OpenHarmony HAL：IoT硬件设备操作接口-GPIO
#include "iot_i2c.h"   // OpenHarmony HAL：IoT硬件设备操作接口-I2C
#include "iot_errno.h" // OpenHarmony HAL：IoT硬件设备操作接口-错误代码定义
#include "hi_io.h"     // 海思 Pegasus SDK：IoT硬件设备操作接口-IO

// 字库头文件
#include "oled_fonts.h"

// OLED显示屏简化版驱动接口文件
#include "oled_ssd1306.h"

// 定义一个宏，用于计算数组的长度
#define ARRAY_SIZE(a) sizeof(a) / sizeof(a[0])

// 定义一个宏，用于标识I2C0
#define OLED_I2C_IDX 0

// 定义一个宏，用于标识I2C0的波特率（传输速率）
#define OLED_I2C_BAUDRATE (400 * 1000) // 400KHz

// 定义一个宏，用于标识OLED的宽度
#define OLED_WIDTH (128)

// 定义一个宏，用于标识SSD1306显示屏驱动芯片的设备地址
#define OLED_I2C_ADDR 0x78

// 定义一个宏，用于标识写命令操作
#define OLED_I2C_CMD 0x00  // 0000 0000       写命令

// 定义一个宏，用于标识写数据操作
#define OLED_I2C_DATA 0x40 // 0100 0000(0x40) 写数据

// 定义一个宏，用于标识100ms的延时
#define DELAY_100_MS (100 * 1000)

// 定义一个结构体，表示要发送或接收的数据
typedef struct
{
    // 要发送的数据的指针
    unsigned char *sendBuf;
    // 要发送的数据长度
    unsigned int sendLen;
    // 要接收的数据的指针
    unsigned char *receiveBuf;
    // 要接收的数据长度
    unsigned int receiveLen;
} IotI2cData;

/// @brief  向OLED写一个字节
/// @param  regAddr 写入命令还是数据 OLED_I2C_CMD / OLED_I2C_DATA
/// @param  byte 写入的内容
/// @retval 成功返回IOT_SUCCESS，失败返回IOT_FAILURE
static uint32_t I2cWiteByte(uint8_t regAddr, uint8_t byte)
{
    // 定义字节流
    uint8_t buffer[] = {regAddr, byte};
    IotI2cData i2cData = {0};
    i2cData.sendBuf = buffer;
    i2cData.sendLen = sizeof(buffer) / sizeof(buffer[0]);

    // 发送字节流
    return IoTI2cWrite(OLED_I2C_IDX, OLED_I2C_ADDR, i2cData.sendBuf, i2cData.sendLen);
}

/// @brief 向OLED写一个命令字节
/// @param cmd 写入的命令字节
/// @return 成功返回IOT_SUCCESS，失败返回IOT_FAILURE
static uint32_t WriteCmd(uint8_t cmd)
{
    return I2cWiteByte(OLED_I2C_CMD, cmd);
}

/// @brief 向OLED写一个数据字节
/// @param cmd 写入的数据字节
/// @return 成功返回IOT_SUCCESS，失败返回IOT_FAILURE
uint32_t WriteData(uint8_t data)
{
    return I2cWiteByte(OLED_I2C_DATA, data);
}

/// @brief 初始化SSD1306显示屏驱动芯片
uint32_t OledInit(void)
{
    // 构造初始化代码
    static const uint8_t initCmds[] = {
        0xAE, // 显示关闭
        0x00, // 页寻址模式时，设置列地址的低4位为0000
        0x10, // 页寻址模式时，设置列地址的高4位为0000
        0x40, // 设置起始行地址为第0行
        0xB0, // 页寻址模式时，设置页面起始地址为PAGE0
        0x81, // 设置对比度
        0xFF, // 对比度数值
        0xA1, // set segment remap
        0xA6, // 设置正常显示。0对应像素熄灭，1对应像素亮起
        0xA8, // --set multiplex ratio(1 to 64)
        0x3F, // --1/32 duty
        0xC8, // Com scan direction
        0xD3, // -set display offset
        0x00, //
        0xD5, // set osc division
        0x80, //
        0xD8, // set area color mode off
        0x05, //
        0xD9, // Set Pre-Charge Period
        0xF1, //
        0xDA, // set com pin configuartion
        0x12, //
        0xDB, // set Vcomh
        0x30, //
        0x8D, // set charge pump enable
        0x14, //
        0xAF, // 显示开启
    };

    // 初始化GPIO-13
    IoTGpioInit(HI_IO_NAME_GPIO_13);
    // 设置GPIO-13引脚功能为I2C0_SDA
    hi_io_set_func(HI_IO_NAME_GPIO_13, HI_IO_FUNC_GPIO_13_I2C0_SDA);
    // 初始化GPIO-14
    IoTGpioInit(HI_IO_NAME_GPIO_14);
    // 设置GPIO-14引脚功能为I2C0_SCL
    hi_io_set_func(HI_IO_NAME_GPIO_14, HI_IO_FUNC_GPIO_14_I2C0_SCL);

    // 用指定的波特速率初始化I2C0
    IoTI2cInit(OLED_I2C_IDX, OLED_I2C_BAUDRATE);

    // 发送初始化代码，初始化SSD1306显示屏驱动芯片
    for (size_t i = 0; i < ARRAY_SIZE(initCmds); i++)
    {
        // 发送一个命令字节
        uint32_t status = WriteCmd(initCmds[i]);
        if (status != IOT_SUCCESS)
        {
            return status;
        }
    }

    // OLED初始化完成，返回成功
    return IOT_SUCCESS;
}

/// @brief 设置显示位置
/// @param x x坐标，1像素为单位
/// @param y y坐标，8像素为单位。即页面起始地址
/// @return 无
void OledSetPosition(uint8_t x, uint8_t y)
{
    //设置页面起始地址
    WriteCmd(0xb0 + y);

    // 列：0~127
    // 第0列：0x00列，二进制00000000。低地址0000，即0x00。高地址0000(需要|0x10)，0000|0x10=0x10。
    // 第127列：0x7f列，二进制01111111。低地址1111，即0x0F。高地址0111(需要|0x10)，0111|0x10=0x17。

    // 设置显示位置：列地址的低4位
    // 直接取出列地址低4位作为命令代码的低4位，命令代码的高4位为0000
    WriteCmd(x & 0x0f);

    // 设置显示位置：列地址的高4位
    // 取出列地址高4位作为命令代码的低4位，命令代码的高4位必须为0001
    // 实际编程时，列地址的高4位和0x10（二进制00010000）进行按位或即得到命令代码
    WriteCmd(((x & 0xf0) >> 4) | 0x10);
}

/// @brief 全屏填充
/// @param fillData 填充的数据，1字节
/// @return 无
void OledFillScreen(uint8_t fillData)
{
    // 相关变量，用于遍历page和列
    uint8_t m = 0;
    uint8_t n = 0;

    // 写入所有页的数据
    for (m = 0; m < 8; m++)
    {
        //设置页地址：0~7
        WriteCmd(0xb0 + m);

        // 设置显示位置为第0列
        WriteCmd(0x00); //设置显示位置：列低地址(0000)
        WriteCmd(0x10); //设置显示位置：列高地址(0000)

        // 写入128列数据
        // 在一个页中，数据按列写入，一次一列，对应发送过来的1字节数据
        for (n = 0; n < 128; n++)
        {
            // 写入一个字节数据
            WriteData(fillData);
        }
    }
}



/// @brief 显示一个字符
/// @param x: x坐标，1像素为单位
/// @param y: y坐标，8像素为单位
/// @param ch: 要显示的字符
/// @param font: 字库
void OledShowChar(uint8_t x, uint8_t y, uint8_t ch, Font font)
{
    // 数组下标
    uint8_t c = 0;

    // 循环控制
    uint8_t i = 0;

    // 得到数组下标
    // 空格的ASCII码32，在字库中的下标是0。字库中的字符-空格即相应的数组下标
    c = ch - ' ';

    // 显示字符
    if (font == FONT8x16) // 8*16的点阵，一个page放不下
    {
        // 显示字符的上半部分
        // 设置显示位置
        OledSetPosition(x, y);
        // 逐个字节写入（16个数组元素的前8个）
        for (i = 0; i < 8; i++)
        {
            WriteData(F8X16[c * 16 + i]);
        }

        // 显示字符的下半部分
        // 设置显示位置为下一个PAGE
        OledSetPosition(x, y + 1);
        // 逐个字节写入（16个数组元素的后8个）
        for (i = 0; i < 8; i++)
        {
            WriteData(F8X16[c * 16 + 8 + i]);
        }
    }
    else // 6*8的点阵，在一个page中
    {
        // 设置显示位置
        OledSetPosition(x, y);
        // 逐个字节写入（数组第二维的6个数组元素）
        for (i = 0; i < 6; i++)
        {
            WriteData(F6x8[c][i]);
        }
    }
}

/// @brief 显示一个字符串
/// @param x: x坐标，1像素为单位
/// @param y: y坐标，8像素为单位
/// @param str: 要显示的字符串
/// @param font: 字库
void OledShowString(uint8_t x, uint8_t y, const char *str, Font font)
{
    // 字符数组（字符串）下标
    uint8_t j = 0;

    // 检查字符串是否为空
    if (str == NULL)
    {
        printf("param is NULL,Please check!!!\r\n");
        return;
    }

    // 遍历字符串，显示每个字符
    while (str[j])
    {
        // 显示一个字符
        OledShowChar(x, y, str[j], font);

        // 设置字符间距
        x += 8;

        // 如果下一个要显示的字符超出了OLED显示的范围，则换行
        if (x > 120)
        {
            x = 0;
            y += 2;
        }

        // 下一个字符
        j++;
    }
}