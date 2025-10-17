# 基于深度学习的车牌识别系统

一个完整的车牌识别系统，支持图片、视频和实时摄像头识别，具备数据库管理、UDP通信和嵌入式设备控制功能。

## 🚀 功能特性

- **多源识别**: 支持图片文件、视频文件和实时摄像头识别
- **数据库管理**: SQLite数据库存储授权车牌和识别记录
- **UDP通信**: 与嵌入式设备进行实时通信
- **OLED显示**: 嵌入式设备OLED屏幕显示车牌和状态
- **舵机控制**: 根据授权状态自动控制路障开关
- **用户友好**: 直观的GUI界面，识别和判断分离设计

## 📋 系统架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   GUI应用   │───▶│ UDP服务器   │───▶│ 嵌入式设备  │
│             │    │             │    │             │
│ • 图片识别  │    │ • 协议转换  │    │ • OLED显示  │
│ • 视频识别  │    │ • 数据库比对│    │ • 舵机控制  │
│ • 摄像头识别│    │ • 数据发送  │    │ • 状态反馈  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐    ┌─────────────┐
│   SQLite    │    │   网络通信   │
│   数据库    │    │   (UDP)     │
└─────────────┘    └─────────────┘
```

## 🛠️ 技术栈

- **后端**: Python 3.x
- **GUI**: Tkinter
- **图像处理**: OpenCV, PIL
- **车牌识别**: HyperLPR3
- **数据库**: SQLite3
- **网络通信**: UDP Socket
- **嵌入式**: C语言 (OpenHarmony)

## 📦 安装要求

### 软件环境
- Python 3.7+
- OpenCV
- HyperLPR3
- Tkinter (通常随Python安装)

### 硬件环境
- 摄像头 (可选)
- 嵌入式设备 (Hi3861开发板)
- OLED显示屏 (SSD1306)
- SG90舵机

## 🔧 安装步骤

### 1. 克隆项目
```bash
git clone https://github.com/JiyliuI/Plate-Recognition-GUI
cd plate_recognition_gui
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 数据库初始化
数据库会在首次运行时自动创建，包含以下表：
- `authorized_plates`: 授权车牌表
- `recognition_records`: 识别记录表

## 🚀 使用方法

### 1. 启动系统

#### 启动UDP服务器
```bash
python udp_server.py
```
服务器将在 `0.0.0.0:9001` 启动，等待客户端连接。

#### 启动GUI应用
```bash
python main.py
```

### 2. 操作流程

#### 手动录入车牌
1. 在"车牌手动录入"区域输入车牌号
2. 选择车牌类型
3. 点击"保存"按钮
4. 车牌信息将保存到数据库

#### 识别车牌
1. **图片识别**: 点击"选取图片"选择包含车牌的图片
2. **视频识别**: 点击"选取视频"选择视频文件
3. **摄像头识别**: 点击"打开相机识别"启动实时识别

#### 开始判断
1. 识别完成后，界面会显示识别结果
2. 点击"开始识别"按钮进行数据库比对
3. 系统显示授权状态并发送给嵌入式设备

### 3. 嵌入式设备

#### 硬件连接
- **OLED显示屏**: I2C接口 (GPIO13-SDA, GPIO14-SCL)
- **SG90舵机**: GPIO2
- **网络**: WiFi连接

#### 编译和烧录
```bash
# 在barrier_gate_client目录下
# 使用OpenHarmony开发环境编译
# 烧录到Hi3861开发板
```

## 📊 数据流程

### 1. 识别阶段
```
用户操作 → 选择图片/视频/摄像头 → 系统识别 → 存储结果 → 显示识别结果
```

### 2. 判断阶段
```
点击"开始识别" → 数据库查询 → 记录识别结果 → 发送UDP消息
```

### 3. 服务器处理
```
接收车牌号 → 数据库比对 → 协议转换 → 发送9字节数据包
```

### 4. 设备响应
```
解析数据包 → OLED显示 → 舵机控制 → 发送确认
```

## 🔌 通信协议

### UDP数据包格式 (9字节)
```
[1字节汉字索引] + [7字节ASCII车牌剩余部分] + [1字节状态索引]
```

### 汉字索引映射
- 0-30: 各省份汉字 (京、沪、津、渝等)
- 31: '禁' (禁止通行)
- 32: '通' (允许通行)
- 33: '行' (动作指示)

### 状态索引
- 31: 禁止通行 → 调用 `GateClose()`
- 32: 允许通行 → 调用 `GateOpen()`

## 🧪 测试

### 运行测试
```bash
# 测试数据库功能
python -c "from gui_handlers import DatabaseManager; db = DatabaseManager(); print('数据库测试通过')"

# 测试UDP协议
python -c "from udp_server import convert_plate_to_car_data; print('协议测试通过')"
```

### 测试用例
1. **授权车牌**: 京A12345 → 应显示"通行"并打开路障
2. **未授权车牌**: 粤D99999 → 应显示"禁行"并保持关闭
3. **摄像头识别**: 实时识别并处理
4. **网络通信**: 验证UDP通信正常

## 📁 项目结构

```
plate_recognition_gui/
├── main.py                 # 主程序入口
├── gui_app.py             # GUI应用主类
├── gui_handlers.py        # 事件处理和业务逻辑
├── gui_styles.py          # GUI样式定义
├── plate_recognition.py   # 车牌识别核心模块
├── plate_utils.py         # 工具函数
├── udp_server.py          # UDP服务器
├── requirements.txt       # 依赖包列表
├── authorized_plates.db   # SQLite数据库
├── barrier_gate_client/   # 嵌入式客户端代码
│   ├── udp_client_test.c  # UDP客户端
│   ├── oled_ssd1306.c     # OLED驱动
│   ├── oled_ssd1306.h     # OLED头文件
│   ├── oled_fonts.h       # 字库定义
│   ├── robot_sg90.c       # 舵机控制
│   └── robot_sg90.h       # 舵机头文件
├── PROJECT_OVERVIEW.md    # 项目概览           
├── QUICKSTART.md          # 快速启动
└── README.md
```

## 🔧 配置说明

### 网络配置
- **UDP服务器端口**: 9001
- **客户端IP**: 127.0.0.1 (本地测试)
- **嵌入式设备IP**: 需要配置为同一网段

### 数据库配置
- **数据库文件**: `authorized_plates.db`
- **自动创建**: 首次运行时自动创建表结构
- **测试数据**: 包含默认的测试车牌

### 硬件配置
- **摄像头索引**: 0 (默认) 或 1
- **OLED地址**: 0x78 (I2C)
- **舵机GPIO**: GPIO2

## 🐛 故障排除

### 常见问题

#### 1. 摄像头无法打开
```bash
# 检查摄像头权限
ls /dev/video*

# 尝试不同的摄像头索引
# 在代码中修改 cv2.VideoCapture(0) 为 cv2.VideoCapture(1)
```

#### 2. UDP连接失败
```bash
# 检查网络连接
ping <embedded-device-ip>

# 检查防火墙设置
sudo ufw status

# 检查端口占用
netstat -tulpn | grep 9001
```

#### 3. 数据库错误
```bash
# 删除数据库文件重新创建
rm authorized_plates.db

# 检查文件权限
ls -la authorized_plates.db
```

#### 4. 识别效果不佳
- 确保图片清晰度足够
- 调整摄像头角度和光线
- 检查车牌是否完整可见



## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目链接: [https://github.com/JiyliuI/Plate-Recognition-GUI](https://github.com/JiyliuI/Plate-Recognition-GUI)
- 问题反馈: [Issues](https://github.com/JiyliuI/Plate-Recognition-GUI/issues)

## 🙏 致谢

- [HyperLPR3](https://github.com/szad670401/HyperLPR3) - 车牌识别引擎
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [OpenHarmony](https://www.openharmony.cn/) - 嵌入式操作系统

---

**注意**: 请确保在使用前仔细阅读测试指南和故障排除部分。如有问题，请查看相关文档或提交Issue。
