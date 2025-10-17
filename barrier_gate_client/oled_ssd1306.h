// OLED显示屏简化版驱动接口文件

// 定义条件编译宏，防止头文件的重复包含和编译
#ifndef OLED_SSD1306_H
#define OLED_SSD1306_H

#include <stdint.h>     // 定义了几种扩展的整数类型和宏

// 声明接口函数

uint32_t OledInit(void);
void OledSetPosition(uint8_t x, uint8_t y);
void OledFillScreen(uint8_t fillData);
uint32_t WriteData(uint8_t data);



// 定义字库类型
enum Font {
    FONT6x8 = 1,
    FONT8x16
};
typedef enum Font Font;

// 声明接口函数

void OledShowChar(uint8_t x, uint8_t y, uint8_t ch, Font font);
void OledShowString(uint8_t x, uint8_t y, const char* str, Font font);

// oled_ssd1306.h (新增函数声明)

/**
 * @brief 显示 16x16 的汉字 (占 2 个 Page)
 * @param x 起始 x 坐标 (0-112)
 * @param y 起始 y 坐标 (Page，0-6)
 * @param index 汉字在 F16X16_CN 数组中的索引 (0-35)
 */
void OledShowCNChar(uint8_t x, uint8_t y, uint8_t index);

// 条件编译结束
#endif // OLED_SSD1306_H
