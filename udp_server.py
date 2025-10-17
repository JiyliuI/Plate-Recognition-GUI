
import socket
import threading
import time
from gui_handlers import DatabaseManager

# 配置服务器地址和端口
UDP_IP = "0.0.0.0"  # 监听所有可用接口，以便接收来自小车的连接
UDP_PORT = 9001
BUFFER_SIZE = 1024

# 全局变量，用于存储嵌入式小车的地址 (UDP是无连接的，但我们可以记录地址用于回复)
CAR_CLIENT_ADDR = None

# 初始化数据库
db_manager = DatabaseManager()

# ----------------------------------------------
# 字符转OLED字库数据映射 (与嵌入式C代码中的字库索引对应)
# 假设嵌入式端在 oled_fonts.h 中添加了 36 个省份汉字字库，从索引 0 开始
# ----------------------------------------------
CHINESE_PLATE_MAPPING = {
    '京': 0, '沪': 1, '津': 2, '渝': 3, '冀': 4, '晋': 5, '蒙': 6, '辽': 7,
    '吉': 8, '黑': 9, '苏': 10, '浙': 11, '皖': 12, '闽': 13, '赣': 14, '鲁': 15,
    '豫': 16, '鄂': 17, '湘': 18, '粤': 19, '桂': 20, '琼': 21, '川': 22, '贵': 23,
    '云': 24, '藏': 25, '陕': 26, '甘': 27, '青': 28, '宁': 29, '新': 30, '禁': 31,
    '通': 32, '行': 33
}

# ----------------------------------------------
# 协议：1字节汉字索引 + 7字节 ASCII + 1字节状态
# 总长度 CAR_DATA_LEN = 9 字节
# ----------------------------------------------
CAR_DATA_LEN = 9


def convert_plate_to_car_data(plate_number, status_index):
    """
    将车牌号和状态索引转换为 9 字节的协议数据包
    协议: [1字节汉字索引] + [7字节 ASCII] + [1字节状态索引]
    """
    if len(plate_number) < 2:
        return b'\xFF' * CAR_DATA_LEN  # 数据无效

    cn_char = plate_number[0]
    rest_plate = plate_number[1:]

    # 1. 汉字索引 (1字节)
    cn_index = CHINESE_PLATE_MAPPING.get(cn_char, 0xFF)  # 0xFF 表示未知汉字

    # 2. 剩余车牌号 (7字节)
    # 填充或截断到 7 字节
    rest_plate_bytes = rest_plate.encode('ascii', 'ignore').ljust(7, b'\x00')

    # 3. 状态索引 (1字节)
    status_byte = bytes([status_index])

    # 组合 9 字节数据包
    car_data = bytes([cn_index]) + rest_plate_bytes + status_byte
    return car_data

def start_udp_server():
    global CAR_CLIENT_ADDR
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((UDP_IP, UDP_PORT))

        print(f"==================================================")
        print(f"|  UDP 服务器启动成功!                          |")
        print(f"|  监听地址: {UDP_IP} (所有接口)                 |")
        print(f"|  监听端口: {UDP_PORT}                           |")
        print(f"==================================================")
        print(f"|  等待接收车牌信息或小车连接...                  |")
        print(f"==================================================")

        while True:
            # 接收数据和客户端地址
            data, addr = server_socket.recvfrom(BUFFER_SIZE)
            message = data.decode('utf-8', 'ignore').strip()

            # 区分客户端类型
            # ==========================================================
            # 1. 嵌入式小车客户端主动连接/心跳 (由 udp_client_test.c 发送)
            # ==========================================================
            if message == "connecting":
                CAR_CLIENT_ADDR = addr  # 记录小车地址
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(f"[{timestamp}] 接收到来自 嵌入式小车({addr}) 的连接/心跳请求.")
                print(f"   [状态] 已记录小车地址，准备回复。")

                # 回复小车一个确认，模拟长连接的“握手”
                ack_response = "ACK:SERVER_READY".encode('utf-8')
                server_socket.sendto(ack_response, addr)
                print("-" * 50)
                continue

            # 如果接收到小车的回执 (ACK:DISPLAYED:...)
            if message.startswith("ACK:DISPLAYED"):
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(f"[{timestamp}] 收到小车({addr})回执: {message}")
                print("-" * 50)
                continue

            # ==========================================================
            # 2. GUI 客户端发送车牌信息
            # ==========================================================
            plate_number = message

            # 打印接收到的信息
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"[{timestamp}] 接收到来自 GUI 客户端({addr}) 的车牌信息:")
            print(f"   车牌号码: {plate_number}")

            # 业务逻辑：比对数据库并确定状态
            status_index = CHINESE_PLATE_MAPPING['禁']  # 默认设置为 '禁'

            # !! 核心比对逻辑 !!
            if db_manager.check_plate_exists(plate_number):
                print("   [业务] 数据库比对：允许通行。")
                status_index = CHINESE_PLATE_MAPPING['通']
                
                # 记录识别记录到数据库
                db_manager.add_recognition_record(
                    plate_number, 
                    source_type="udp_server", 
                    is_authorized=True, 
                    action_taken="allow"
                )
            else:
                print("   [业务] 数据库比对：禁止通行。")
                status_index = CHINESE_PLATE_MAPPING['禁']
                
                # 记录识别记录到数据库
                db_manager.add_recognition_record(
                    plate_number, 
                    source_type="udp_server", 
                    is_authorized=False, 
                    action_taken="deny"
                )

            # 动作指示（'行' 索引）
            action_index = CHINESE_PLATE_MAPPING['行']

            # 发送给嵌入式小车
            if CAR_CLIENT_ADDR:
                # 转换数据格式，发送放行状态和动作指示
                # 我们将 “通行/禁行” 索引放在第 9 字节 (索引 8)
                car_data = convert_plate_to_car_data(plate_number, status_index)

                # 发送给嵌入式小车
                try:
                    server_socket.sendto(car_data, CAR_CLIENT_ADDR)
                    print(f"   [小车通信] 成功发送 {len(car_data)} 字节车牌数据和状态数据到小车: {CAR_CLIENT_ADDR}")
                except Exception as e:
                    print(f"   [小车通信] 发送给小车失败: {e}")
            else:
                print("   [小车通信] 警告: 嵌入式小车客户端地址未知，无法发送数据。")

            print("-" * 50)

    except KeyboardInterrupt:
        print("\n[服务器] 程序关闭。")
    except Exception as e:
        print(f"\n[服务器] 发生错误: {e}")
    finally:
        if 'server_socket' in locals():
            server_socket.close()


if __name__ == "__main__":
    start_udp_server()