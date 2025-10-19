import socket
import threading
import time
from gui_handlers import DatabaseManager

# 配置服务器地址和端口
UDP_IP = "0.0.0.0"  # 监听所有可用接口
UDP_PORT = 9001  # 界面服务器端口
BARRIER_PORT = 8081  # 闸机服务器端口
BUFFER_SIZE = 1024

# 全局变量
CAR_CLIENT_ADDR = None  # 嵌入式小车地址
BARRIER_CLIENTS = {}  # 闸机客户端字典
db_manager = DatabaseManager()

# ----------------------------------------------
# 字符转OLED字库数据映射
# ----------------------------------------------
CHINESE_PLATE_MAPPING = {
    '京': 0, '沪': 1, '津': 2, '渝': 3, '冀': 4, '晋': 5, '蒙': 6, '辽': 7,
    '吉': 8, '黑': 9, '苏': 10, '浙': 11, '皖': 12, '闽': 13, '赣': 14, '鲁': 15,
    '豫': 16, '鄂': 17, '湘': 18, '粤': 19, '桂': 20, '琼': 21, '川': 22, '贵': 23,
    '云': 24, '藏': 25, '陕': 26, '甘': 27, '青': 28, '宁': 29, '新': 30, '禁': 31,
    '通': 32, '行': 33
}

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
    rest_plate_bytes = rest_plate.encode('ascii', 'ignore').ljust(7, b'\x00')

    # 3. 状态索引 (1字节)
    status_byte = bytes([status_index])

    # 组合 9 字节数据包
    car_data = bytes([cn_index]) + rest_plate_bytes + status_byte
    return car_data


def send_to_barrier_gate(plate_number, status):
    """
    发送控制命令到闸机单片机
    新格式: 汉字索引,剩余车牌号,执行命令 (例如: 1,A10002,0)
    执行命令: 0=打开闸机, 1=关闭闸机, 2=停止
    """
    if not BARRIER_CLIENTS:
        print("   [闸机通信] 警告: 没有连接的闸机客户端")
        return False

    # 解析车牌号获取汉字索引和剩余部分
    if len(plate_number) < 2:
        print(f"   [闸机通信] 错误: 车牌号格式不正确: {plate_number}")
        return False

    cn_char = plate_number[0]
    rest_plate = plate_number[1:]

    # 获取汉字索引
    cn_index = CHINESE_PLATE_MAPPING.get(cn_char, 0xFF)

    # 构建新的控制命令格式: 汉字索引,剩余车牌号,执行命令
    if status == "allow":
        # 允许通行 - 打开闸机
        command = f"{cn_index},{rest_plate},0"  # 0表示打开闸机
        print(f"   [闸机控制] 发送打开闸机命令: {command}")
    else:
        # 禁止通行 - 关闭闸机
        command = f"{cn_index},{rest_plate},1"  # 1表示关闭闸机
        print(f"   [闸机控制] 发送关闭闸机命令: {command}")

    success_count = 0
    for addr in list(BARRIER_CLIENTS.keys()):
        try:
            barrier_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            barrier_socket.settimeout(2.0)  # 设置超时
            barrier_socket.sendto(command.encode('utf-8'), addr)

            # 等待单片机响应
            try:
                response, _ = barrier_socket.recvfrom(BUFFER_SIZE)
                response_msg = response.decode('utf-8', 'ignore').strip()
                print(f"   [闸机响应] 来自 {addr}: {response_msg}")
            except socket.timeout:
                print(f"   [闸机响应] 来自 {addr}: 超时未收到响应")

            barrier_socket.close()
            print(f"   [闸机通信] 成功发送控制命令到闸机 {addr}: {command}")
            success_count += 1
        except Exception as e:
            print(f"   [闸机通信] 发送到闸机 {addr} 失败: {e}")

    return success_count > 0


def send_direct_command_to_barrier(command_type):
    """
    发送直接控制命令到闸机
    command_type: "OPEN" 或 "CLOSE"
    """
    if not BARRIER_CLIENTS:
        print("   [闸机通信] 警告: 没有连接的闸机客户端")
        return False

    # 构建直接控制命令
    if command_type == "OPEN":
        command = "99,OPEN,0"  # 使用特殊汉字索引99表示直接控制，0表示打开
        print(f"   [直接控制] 发送打开闸机命令: {command}")
    elif command_type == "CLOSE":
        command = "99,CLOSE,1"  # 使用特殊汉字索引99表示直接控制，1表示关闭
        print(f"   [直接控制] 发送关闭闸机命令: {command}")
    else:
        print(f"   [直接控制] 错误: 未知命令类型: {command_type}")
        return False

    success_count = 0
    for addr in list(BARRIER_CLIENTS.keys()):
        try:
            barrier_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            barrier_socket.settimeout(2.0)  # 设置超时
            barrier_socket.sendto(command.encode('utf-8'), addr)

            # 等待单片机响应
            try:
                response, _ = barrier_socket.recvfrom(BUFFER_SIZE)
                response_msg = response.decode('utf-8', 'ignore').strip()
                print(f"   [闸机响应] 来自 {addr}: {response_msg}")
            except socket.timeout:
                print(f"   [闸机响应] 来自 {addr}: 超时未收到响应")

            barrier_socket.close()
            print(f"   [直接控制] 成功发送控制命令到闸机 {addr}: {command}")
            success_count += 1
        except Exception as e:
            print(f"   [直接控制] 发送到闸机 {addr} 失败: {e}")

    return success_count > 0


def start_plate_server():
    """启动车牌识别服务器（端口9001）"""
    global CAR_CLIENT_ADDR

    try:
        plate_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        plate_socket.bind((UDP_IP, UDP_PORT))

        print(f"==================================================")
        print(f"|  车牌识别服务器启动成功!                       |")
        print(f"|  监听地址: {UDP_IP}:{UDP_PORT}                    |")
        print(f"==================================================")
        print(f"|  等待接收车牌信息或小车连接...                  |")
        print(f"==================================================")

        while True:
            data, addr = plate_socket.recvfrom(BUFFER_SIZE)
            message = data.decode('utf-8', 'ignore').strip()

            # 检查是否为直接控制命令 (OPEN/CLOSE)
            if message.upper() in ["OPEN", "CLOSE"]:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(f"[{timestamp}] 接收到来自 GUI 客户端({addr}) 的直接控制命令:")
                print(f"   控制命令: {message}")

                # 处理直接控制命令
                success = send_direct_command_to_barrier(message.upper())
                if success:
                    print("   [直接控制] 命令发送成功")
                    # 回复确认
                    ack_response = f"ACK:{message.upper()}_SENT".encode('utf-8')
                    plate_socket.sendto(ack_response, addr)
                else:
                    print("   [直接控制] 命令发送失败")
                    # 回复错误
                    error_response = f"ERROR:{message.upper()}_FAILED".encode('utf-8')
                    plate_socket.sendto(error_response, addr)

                print("-" * 50)
                continue

            # 嵌入式小车客户端主动连接/心跳
            if message == "connecting":
                CAR_CLIENT_ADDR = addr
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(f"[{timestamp}] 接收到来自 嵌入式小车({addr}) 的连接/心跳请求.")
                print(f"   [状态] 已记录小车地址，准备回复。")

                # 回复确认
                ack_response = "ACK:SERVER_READY".encode('utf-8')
                plate_socket.sendto(ack_response, addr)
                print("-" * 50)
                continue

            # 如果接收到小车的回执
            if message.startswith("ACK:DISPLAYED"):
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(f"[{timestamp}] 收到小车({addr})回执: {message}")
                print("-" * 50)
                continue

            # GUI 客户端发送车牌信息
            plate_number = message

            # 打印接收到的信息
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"[{timestamp}] 接收到来自 GUI 客户端({addr}) 的车牌信息:")
            print(f"   车牌号码: {plate_number}")

            # 业务逻辑：比对数据库并确定状态
            status_index = CHINESE_PLATE_MAPPING['禁']  # 默认设置为 '禁'
            status_text = "deny"

            if db_manager.check_plate_exists(plate_number):
                print("   [业务] 数据库比对：允许通行。")
                status_index = CHINESE_PLATE_MAPPING['通']
                status_text = "allow"

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
                status_text = "deny"

                # 记录识别记录到数据库
                db_manager.add_recognition_record(
                    plate_number,
                    source_type="udp_server",
                    is_authorized=False,
                    action_taken="deny"
                )

            # 发送给嵌入式小车（显示）
            if CAR_CLIENT_ADDR:
                car_data = convert_plate_to_car_data(plate_number, status_index)
                try:
                    plate_socket.sendto(car_data, CAR_CLIENT_ADDR)
                    print(f"   [小车通信] 成功发送 {len(car_data)} 字节车牌数据和状态数据到小车: {CAR_CLIENT_ADDR}")

                    # 等待小车确认
                    plate_socket.settimeout(3.0)
                    try:
                        ack_data, _ = plate_socket.recvfrom(BUFFER_SIZE)
                        ack_msg = ack_data.decode('utf-8', 'ignore').strip()
                        if ack_msg.startswith("ACK:DISPLAYED"):
                            print(f"   [小车确认] 显示成功: {ack_msg}")
                    except socket.timeout:
                        print("   [小车确认] 超时未收到确认")
                    plate_socket.settimeout(None)  # 取消超时

                except Exception as e:
                    print(f"   [小车通信] 发送给小车失败: {e}")
            else:
                print("   [小车通信] 警告: 嵌入式小车客户端地址未知，无法发送数据。")

            # 发送给闸机单片机（控制）- 使用新格式
            barrier_success = send_to_barrier_gate(plate_number, status_text)
            if barrier_success:
                print("   [系统] 闸机控制命令发送成功")
            else:
                print("   [系统] 闸机控制命令发送失败")

            print("-" * 50)

    except KeyboardInterrupt:
        print("\n[车牌服务器] 程序关闭。")
    except Exception as e:
        print(f"\n[车牌服务器] 发生错误: {e}")
    finally:
        if 'plate_socket' in locals():
            plate_socket.close()


def start_barrier_server():
    """启动闸机控制服务器（端口8081）"""

    try:
        barrier_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        barrier_socket.bind((UDP_IP, BARRIER_PORT))
        barrier_socket.settimeout(1.0)  # 设置超时以便可以检查运行状态

        print(f"==================================================")
        print(f"|  闸机控制服务器启动成功!                       |")
        print(f"|  监听地址: {UDP_IP}:{BARRIER_PORT}                  |")
        print(f"==================================================")
        print("|  等待闸机单片机连接...                         |")
        print(f"==================================================")

        running = True

        while running:
            try:
                data, addr = barrier_socket.recvfrom(BUFFER_SIZE)
                message = data.decode('utf-8').strip()

                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                if addr not in BARRIER_CLIENTS:
                    BARRIER_CLIENTS[addr] = {
                        'connect_time': time.time(),
                        'last_heartbeat': time.time(),
                        'status': 'connected'
                    }
                    print(f"[{timestamp}] 🆕 新闸机单片机连接: {addr}")
                    print(f"   [状态] 当前连接的闸机数量: {len(BARRIER_CLIENTS)}")

                # 更新最后通信时间
                BARRIER_CLIENTS[addr]['last_heartbeat'] = time.time()

                print(f"[{timestamp}] 📥 收到来自闸机 {addr} 的消息: {message}")

                # 处理不同类型的单片机消息
                if "Barrier_Ready" in message:
                    print(f"   [闸机状态] 设备已就绪，等待控制命令...")
                    # 回复确认
                    response = "ACK:BARRIER_READY".encode('utf-8')
                    barrier_socket.sendto(response, addr)

                elif "ACK:OPEN" in message:
                    print(f"   [闸机动作] 闸机已打开")

                elif "ACK:CLOSE" in message:
                    print(f"   [闸机动作] 闸机已关闭")

                elif "HEARTBEAT" in message:
                    # 心跳包，已更新最后通信时间
                    pass

            except socket.timeout:
                # 检查超时的客户端
                current_time = time.time()
                timeout_clients = []
                for client_addr, client_info in BARRIER_CLIENTS.items():
                    if current_time - client_info['last_heartbeat'] > 10:  # 10秒超时
                        timeout_clients.append(client_addr)

                # 移除超时客户端
                for client_addr in timeout_clients:
                    del BARRIER_CLIENTS[client_addr]
                    print(f"[超时清理] 移除超时闸机客户端: {client_addr}")

            except Exception as e:
                if running:
                    print(f"[闸机服务器] 接收错误: {e}")

    except KeyboardInterrupt:
        print("\n[闸机服务器] 程序关闭。")
        running = False
    except Exception as e:
        print(f"\n[闸机服务器] 发生错误: {e}")
    finally:
        if 'barrier_socket' in locals():
            barrier_socket.close()


def handle_user_input():
    """处理用户输入命令"""
    print(f"\n🎮 用户命令控制台已启动")
    print("输入 'help' 查看可用命令")

    while True:
        try:
            user_input = input("\n输入命令: ").strip()

            if user_input.lower() == 'quit':
                print("退出用户命令控制台")
                break
            elif user_input.lower() == 'help':
                print("可用命令:")
                print("  list - 列出连接的客户端")
                print("  test - 发送测试序列")
                print("  status - 显示系统状态")
                print("  clear - 清空客户端列表")
                print("  open - 发送打开闸机命令")
                print("  close - 发送关闭闸机命令")
                print("  quit - 退出命令控制台")
                print("  新格式命令: 汉字索引,剩余车牌号,执行命令")
                print("  例如: 1,A10002,1  (1=打开, 0=关闭, 2=停止)")
                print("  简单命令: open, close, stop, ready")
            elif user_input.lower() == 'list':
                list_clients()
            elif user_input.lower() == 'test':
                send_test_sequence()
            elif user_input.lower() == 'status':
                show_system_status()
            elif user_input.lower() == 'clear':
                clear_clients()
            elif user_input.lower() == 'open':
                # 发送直接打开命令
                send_direct_command_to_barrier("OPEN")
            elif user_input.lower() == 'close':
                # 发送直接关闭命令
                send_direct_command_to_barrier("CLOSE")
            elif user_input:
                # 发送到所有闸机客户端
                broadcast_to_barrier(user_input)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"输入错误: {e}")


def list_clients():
    """列出所有连接的客户端"""
    print(f"\n📋 连接的客户端:")

    # 嵌入式小车状态
    if CAR_CLIENT_ADDR:
        print(f"  🚗 嵌入式小车: {CAR_CLIENT_ADDR} (已连接)")
    else:
        print("  🚗 嵌入式小车: 未连接")

    # 闸机设备状态
    if BARRIER_CLIENTS:
        print(f"  🚦 闸机设备 ({len(BARRIER_CLIENTS)}个):")
        for i, (addr, client_info) in enumerate(BARRIER_CLIENTS.items(), 1):
            duration = time.time() - client_info['connect_time']
            last_contact = time.time() - client_info['last_heartbeat']
            status = "正常" if last_contact < 5 else "警告"
            print(f"    {i}. {addr}")
            print(f"       连接时间: {duration:.1f}秒, 最后通信: {last_contact:.1f}秒前 [{status}]")
    else:
        print("  🚦 闸机设备: 无连接")


def show_system_status():
    """显示系统状态"""
    print(f"\n📊 系统状态概览:")
    print(f"  车牌服务器: 运行中 (端口 {UDP_PORT})")
    print(f"  闸机服务器: 运行中 (端口 {BARRIER_PORT})")
    print(f"  数据库连接: 正常")
    print(f"  嵌入式小车: {'已连接' if CAR_CLIENT_ADDR else '未连接'}")
    print(f"  闸机单片机: {len(BARRIER_CLIENTS)} 个连接")


def clear_clients():
    """清空客户端列表"""
    global CAR_CLIENT_ADDR, BARRIER_CLIENTS
    CAR_CLIENT_ADDR = None
    BARRIER_CLIENTS.clear()
    print("✅ 已清空所有客户端连接记录")


def send_test_sequence():
    """发送测试序列"""
    if not BARRIER_CLIENTS:
        print("❌ 没有连接的闸机客户端")
        return

    test_commands = [
        "ready",  # 设备就绪
        "1,A10001,1",  # 打开闸机 - 鄂A10001
        "1,B20002,0",  # 关闭闸机 - 鄂B20002
        "1,C30003,2",  # 停止状态 - 鄂C30003
        "17,A12345,1",  # 打开闸机 - 鄂A12345 (17是鄂的索引)
        "17,B67890,0",  # 关闭闸机 - 鄂B67890
        "OPEN",  # 直接打开命令
        "CLOSE",  # 直接关闭命令
    ]

    print(f"\n🧪 开始测试序列...")
    for cmd in test_commands:
        print(f"  发送: {cmd}")
        if cmd.upper() in ["OPEN", "CLOSE"]:
            send_direct_command_to_barrier(cmd.upper())
        else:
            broadcast_to_barrier(cmd)
        time.sleep(2)  # 等待2秒


def broadcast_to_barrier(message):
    """广播消息到所有闸机客户端"""
    if not BARRIER_CLIENTS:
        print("❌ 没有连接的闸机客户端")
        return False

    success_count = 0
    for addr in list(BARRIER_CLIENTS.keys()):
        try:
            barrier_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            barrier_socket.settimeout(2.0)
            barrier_socket.sendto(message.encode('utf-8'), addr)

            # 等待响应
            try:
                response, _ = barrier_socket.recvfrom(BUFFER_SIZE)
                response_msg = response.decode('utf-8', 'ignore').strip()
                print(f"  📤 发送到闸机 {addr}: {message} -> 响应: {response_msg}")
            except socket.timeout:
                print(f"  📤 发送到闸机 {addr}: {message} -> 无响应")

            barrier_socket.close()
            success_count += 1
        except Exception as e:
            print(f"  发送到闸机 {addr} 错误: {e}")

    return success_count > 0


def main():
    """主函数"""
    print("=" * 60)
    print("       智能车牌识别系统 - 双服务器模式")
    print("=" * 60)
    print("系统组件:")
    print("  🚗 车牌识别服务器 (端口 9001) - 处理GUI和小车通信")
    print("  🚦 闸机控制服务器 (端口 8081) - 处理单片机通信")
    print("  💾 数据库管理 - 车牌验证和记录存储")
    print("=" * 60)
    print("通信协议:")
    print("  发送给闸机格式: 汉字索引,剩余车牌号,执行命令")
    print("  示例: 1,A10002,0 (0=打开, 1=关闭, 2=停止)")
    print("  直接控制命令: OPEN, CLOSE")
    print("=" * 60)

    # 启动车牌服务器线程
    plate_thread = threading.Thread(target=start_plate_server, daemon=True)
    plate_thread.start()
    print("✅ 车牌识别服务器线程已启动")

    # 启动闸机服务器线程
    barrier_thread = threading.Thread(target=start_barrier_server, daemon=True)
    barrier_thread.start()
    print("✅ 闸机控制服务器线程已启动")

    # 给服务器启动时间
    time.sleep(1)

    # 在主线程中处理用户输入
    try:
        handle_user_input()
    except KeyboardInterrupt:
        print("\n\n系统关闭中...")
    finally:
        print("系统已关闭")


if __name__ == "__main__":
    main()