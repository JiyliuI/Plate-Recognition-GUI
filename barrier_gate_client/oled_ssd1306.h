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

// 条件编译结束
#endif // OLED_SSD1306_H