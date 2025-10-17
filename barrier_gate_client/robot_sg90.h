#ifndef ROBOT_SG90_H
#define ROBOT_SG90_H

#include <stdint.h>

// 舵机控制函数声明

/**
 * @brief 设置舵机角度
 * @param duty 高电平时间（微秒），范围500-2500
 */
void set_angle(unsigned int duty);

/**
 * @brief 舵机左转
 * 控制舵机向左旋转45度
 */
void engine_turn_left(void);

/**
 * @brief 舵机右转
 * 控制舵机向右旋转45度
 */
void engine_turn_right(void);

/**
 * @brief 舵机居中
 * 控制舵机回到中间位置
 */
void regress_middle(void);

/**
 * @brief 打开路障
 * 控制舵机打开路障，用于授权通过的情况
 */
void GateOpen(void);

/**
 * @brief 关闭路障
 * 控制舵机关闭路障，用于未授权的情况
 */
void GateClose(void);

#endif // ROBOT_SG90_H
