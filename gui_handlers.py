import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import cv2
import os
import socket
import sys
import sqlite3

# 文本转语音（本地）
try:
    import pyttsx3

    _tts_engine = pyttsx3.init()

    try:
        voices = _tts_engine.getProperty('voices')
        selected_voice_id = None
        for v in voices:
            name = getattr(v, 'name', '') or ''
            lang_list = getattr(v, 'languages', []) or []
            lang_text = ' '.join([
                (x.decode('utf-8', errors='ignore') if isinstance(x, (bytes, bytearray)) else str(x))
                for x in lang_list
            ])
            vid = getattr(v, 'id', '') or ''
            check_text = f"{name} {lang_text} {vid}".lower()
            if ('zh' in check_text) or ('chinese' in check_text) or ('cmn' in check_text):
                selected_voice_id = v.id
                break
        if selected_voice_id:
            _tts_engine.setProperty('voice', selected_voice_id)
        # 设置适中的语速与音量
        try:
            rate = _tts_engine.getProperty('rate')
            if isinstance(rate, int):
                _tts_engine.setProperty('rate', max(80, min(rate, 150)))
            _tts_engine.setProperty('volume', 1.0)
        except Exception:
            pass
    except Exception:
        pass
except Exception:
    pyttsx3 = None
    _tts_engine = None


def speak_text(text):
    """使用本地扬声器播报文本（失败时静默忽略）。"""
    try:
        if _tts_engine is None:
            return

        # 避免阻塞UI线程，开子线程执行朗读
        def _run():
            try:
                _tts_engine.say(text)
                _tts_engine.runAndWait()
            except Exception:
                pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()
    except Exception:
        pass


# 确保在运行前创建 plate_utils.py 和 plate_recognition.py
try:
    from plate_utils import calculate_runtime
    from plate_recognition import process_source
except ImportError:
    # 临时占位符，防止导入错误
    def calculate_runtime(func, *args, **kwargs):
        print("Warning: myUtils.calculate_runtime not found. Using placeholder.")
        return 0.1, None  # 模拟运行时长和返回值


    def process_source(filename, save_path=None):
        print("Warning: myIdentify.process_source not found. Using placeholder.")
        # 模拟返回一个识别结果和一张 PIL Image 对象
        if 'image' in filename:
            mock_plate = "津A88888"
        else:
            mock_plate = "沪B99999"

        mock_image = Image.new('RGB', (200, 100), color='blue')
        return [(mock_plate, mock_image)]


# ----------------------------------------------
# 数据库管理类
# ----------------------------------------------
class DatabaseManager:
    """ 管理车牌授权列表的 SQLite 数据库操作 """

    def __init__(self, db_name='authorized_plates.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        """ 建立数据库连接 """
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.conn.cursor()
            print(f"[DB] 数据库 '{self.db_name}' 连接成功。")
        except sqlite3.Error as e:
            print(f"[DB ERROR] 连接数据库失败: {e}")

    def create_tables(self):
        """ 创建数据库表结构 """
        if not self.conn:
            return

        # 创建授权车牌表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorized_plates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT UNIQUE NOT NULL,
                plate_type TEXT DEFAULT '普通车牌',
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建识别记录表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS recognition_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL,
                recognition_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_type TEXT DEFAULT 'camera',
                is_authorized BOOLEAN DEFAULT 0,
                action_taken TEXT DEFAULT 'deny'
            )
        """)

        self.conn.commit()

        # 插入测试数据 (如果不存在)
        self._insert_test_data()

        print("[DB] 数据库表创建/检查完毕。")

    def _insert_test_data(self):
        """ 插入测试数据 """
        test_plates = [
            ('京A88888', '普通车牌', '授权测试车辆'),
            ('津A12345', '普通车牌', '授权测试车辆2'),
            ('沪B99999', '普通车牌', '授权测试车辆3'),
            ('粤C11111', '普通车牌', '授权测试车辆4')
        ]

        for plate_number, plate_type, comment in test_plates:
            try:
                self.cursor.execute("""
                    INSERT INTO authorized_plates (plate_number, plate_type, comment) 
                    VALUES (?, ?, ?)
                """, (plate_number, plate_type, comment))
            except sqlite3.IntegrityError:
                # UNIQUE 约束冲突，忽略
                pass

        self.conn.commit()
        print("[DB] 测试数据插入完成。")

    def add_authorized_plate(self, plate_number, plate_type='普通车牌', comment=''):
        """ 添加授权车牌 """
        if not self.conn:
            return False

        try:
            self.cursor.execute("""
                INSERT INTO authorized_plates (plate_number, plate_type, comment) 
                VALUES (?, ?, ?)
            """, (plate_number, plate_type, comment))
            self.conn.commit()
            print(f"[DB] 成功添加授权车牌: {plate_number}")
            return True
        except sqlite3.IntegrityError:
            print(f"[DB] 车牌 {plate_number} 已存在")
            return False
        except sqlite3.Error as e:
            print(f"[DB ERROR] 添加车牌失败: {e}")
            return False

    def check_plate_exists(self, plate_number):
        """ 检查车牌号是否在授权列表中 """
        if not self.conn:
            return False

        self.cursor.execute(
            "SELECT plate_number FROM authorized_plates WHERE plate_number=?",
            (plate_number,)
        )
        return self.cursor.fetchone() is not None

    def get_all_authorized_plates(self):
        """ 获取所有授权车牌 """
        if not self.conn:
            return []

        self.cursor.execute("""
            SELECT plate_number, plate_type, comment, created_at 
            FROM authorized_plates 
            ORDER BY created_at DESC
        """)
        return self.cursor.fetchall()

    def delete_authorized_plate(self, plate_number):
        """ 删除授权车牌 """
        if not self.conn:
            return False

        try:
            self.cursor.execute("DELETE FROM authorized_plates WHERE plate_number=?", (plate_number,))
            self.conn.commit()
            if self.cursor.rowcount > 0:
                print(f"[DB] 成功删除授权车牌: {plate_number}")
                return True
            else:
                print(f"[DB] 车牌 {plate_number} 不存在")
                return False
        except sqlite3.Error as e:
            print(f"[DB ERROR] 删除车牌失败: {e}")
            return False

    def add_recognition_record(self, plate_number, source_type='camera', is_authorized=False, action_taken='deny'):
        """ 添加识别记录 """
        if not self.conn:
            return False

        try:
            self.cursor.execute("""
                INSERT INTO recognition_records (plate_number, source_type, is_authorized, action_taken) 
                VALUES (?, ?, ?, ?)
            """, (plate_number, source_type, is_authorized, action_taken))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"[DB ERROR] 添加识别记录失败: {e}")
            return False

    def get_recognition_records(self, limit=100):
        """ 获取识别记录 """
        if not self.conn:
            return []

        self.cursor.execute("""
            SELECT plate_number, recognition_time, source_type, is_authorized, action_taken 
            FROM recognition_records 
            ORDER BY recognition_time DESC 
            LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()

    def close(self):
        """ 关闭数据库连接 """
        if self.conn:
            self.conn.close()
            print("[DB] 数据库连接已关闭。")


class GUIHandlers:
    """ 负责所有事件处理、业务逻辑、线程管理和资源操作 """

    def __init__(self):
        # 数据库管理器
        self.db_manager = DatabaseManager()

        # UDP 协议汉字和状态映射 (必须与嵌入式C代码一致)
        # 0-35 是省份，31 是 '禁'，32 是 '通' (请根据您的 oled_fonts.h 调整)
        self.CHINESE_PLATE_MAPPING = {
            '京': 0, '沪': 1, '津': 2, '渝': 3, '冀': 4, '晋': 5, '蒙': 6, '辽': 7,
            '吉': 8, '黑': 9, '苏': 10, '浙': 11, '皖': 12, '闽': 13, '赣': 14, '鲁': 15,
            '豫': 16, '鄂': 17, '湘': 18, '粤': 19, '桂': 20, '琼': 21, '川': 22, '贵': 23,
            '云': 24, '藏': 25, '陕': 26, '甘': 27, '青': 28, '宁': 29, '新': 30,
            # '禁'/'通' 的索引，用于状态字段
            '禁': 31,  # 拒绝放行状态
            '通': 32  # 允许放行状态
        }

    def init_udp_client(self):
        """ 初始化 UDP 客户端 (新增控制台调试打印) """
        try:
            # 创建 UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.system_status.set(f"🟢 系统运行正常 | UDP: {self.udp_server_ip}:{self.udp_server_port} 连接就绪")
            print(f"[UDP 客户端] 初始化成功，目标服务器: {self.udp_server_ip}:{self.udp_server_port}")  # <--- 调试打印
        except Exception as e:
            self.system_status.set(f"🔴 系统错误 | UDP 初始化失败: {e}")
            messagebox.showerror("错误", f"UDP 客户端初始化失败: {e}")

    def send_plate_number_via_udp(self, plate_number):
        """ 发送车牌号信息到 UDP 服务器 """
        if self.udp_socket is None:
            print("[UDP] 客户端未初始化，无法发送。")
            return

        try:
            # 发送车牌号到UDP服务器（服务器会进行数据库比对并发送结果给嵌入式设备）
            message = plate_number.encode('utf-8')
            self.udp_socket.sendto(message, (self.udp_server_ip, self.udp_server_port))

            print(f"[UDP] 成功发送车牌号: {plate_number}")
            self.root.after(0, lambda: self.system_status.set(
                f"🟢 车牌: {plate_number} | UDP 发送成功 | 等待服务器处理"
            ))

        except Exception as e:
            print(f"[UDP] 发送失败: {e}")
            self.root.after(0, lambda: self.system_status.set(f"🔴 车牌: {plate_number} | UDP 发送失败"))

    def select_image_file(self):
        """ 选择本地图片 """
        filename = filedialog.askopenfilename(
            title="选择车辆图像",
            filetypes=[("图像文件", "*.jpg *.jpeg *.png *.bmp"), ("所有文件", "*.*")]
        )
        if filename:
            try:
                # 加载并显示图像 (左侧大图)
                image = Image.open(filename)
                image.thumbnail((350, 250))
                photo = ImageTk.PhotoImage(image)

                self.image_label.configure(image=photo, text="")
                self.image_label.image = photo

                self.selected_image_path = filename

                # 启动识别并在线程中处理
                threading.Thread(target=self._process_file_recognition, args=(filename,), daemon=True).start()

                return filename

            except Exception as e:
                messagebox.showerror("错误", f"无法加载图像: {str(e)}")

    def select_video_file(self):
        """ 选择本地视频文件 """
        filename = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv"), ("所有文件", "*.*")]
        )
        if filename:
            self.current_video_path = filename
            self.system_status.set(f"🟢 已选择视频文件: {os.path.basename(filename)}")
            self.show_video_viewer(filename)

            # 视频文件选择后，立即进行一次识别预览
            threading.Thread(target=self._process_file_recognition, args=(filename,), daemon=True).start()

            return filename

    def _process_file_recognition(self, filename):
        """ 用于文件（图片/视频）识别的独立线程函数 """
        try:
            self.root.after(0, lambda: self.process_time_var.set("识别中..."))
            self.root.after(0, lambda: self.plate_number_var.set("处理中..."))

            cropped_results = process_source(filename)
            _runtime, _ = calculate_runtime(process_source, filename)

            if cropped_results:
                plate_number, plate_image = cropped_results[0]  # 只处理第一个识别结果

                # 存储识别结果，等待"开始识别"按钮点击
                self.last_recognition_result = (plate_number, plate_image)
                self.recognition_source_type = "file"

                # 更新界面显示
                self.root.after(0, lambda: self.plate_number_var.set(plate_number))
                self.root.after(0, lambda: self.process_time_var.set(f"{_runtime:.2f}秒"))
                self.root.after(0, lambda: self.plate_image_label.config(text="车牌已校正", bg='#d5edff'))
                self.root.after(0, lambda: self.system_status.set(
                    f"🟢 识别完成 | 车牌: {plate_number} | 点击'开始识别'进行判断"))

                # 更新校正车牌图像显示
                self.root.after(0, lambda: self.update_plate_image_display(plate_image))

        except Exception as e:
            print(f"文件识别处理错误: {e}")
            self.root.after(0, lambda: self.plate_number_var.set("识别失败"))
            self.root.after(0, lambda: self.process_time_var.set("错误"))

    def start_recognition(self):
        """ 开始识别（进行数据库比对和UDP发送）"""
        # 检查是否有识别结果
        if not self.last_recognition_result:
            messagebox.showwarning("警告", "请先进行车牌识别（选择图片、视频或打开摄像头）")
            return

        plate_number, plate_image = self.last_recognition_result
        source_type = self.recognition_source_type or "unknown"

        try:
            # 检查车牌是否在授权列表中
            is_authorized = self.db_manager.check_plate_exists(plate_number)

            # 记录识别记录到数据库
            action_taken = "allow" if is_authorized else "deny"
            self.db_manager.add_recognition_record(
                plate_number,
                source_type=source_type,
                is_authorized=is_authorized,
                action_taken=action_taken
            )

            # 更新状态显示
            status_msg = "授权通过" if is_authorized else "未授权"
            self.system_status.set(f"🟢 识别判断完成 | 车牌: {plate_number} | 状态: {status_msg}")

            # 本地播报：车牌号 + 通/禁行
            try:
                speak_text(f"{plate_number}，{'通行' if is_authorized else '禁行'}")
            except Exception:
                pass

            # 发送UDP消息到服务器
            self.send_plate_number_via_udp(plate_number)

            # 显示结果消息
            messagebox.showinfo("识别结果", f"车牌号码: {plate_number}\n授权状态: {status_msg}\n")

        except Exception as e:
            print(f"开始识别处理错误: {e}")
            messagebox.showerror("错误", f"处理识别结果时出错: {str(e)}")

    def open_camera_with_recognition(self):
        """打 开摄像头并开始车牌识别 """
        if self.is_camera_running:
            messagebox.showinfo("提示", "摄像头已经在运行")
            return

        try:
            # 打开摄像头
            if sys.platform.startswith("win"):
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            else:
                self.cap = cv2.VideoCapture(0)

            # 尝试 1 号摄像头
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(1)

            if self.cap.isOpened():
                self.is_camera_running = True
                self.is_camera_detecting = True
                self.seen_plates.clear()  # 清空已识别车牌记录

                self.video_label.config(text="摄像头启动中...", fg='#f1c40f')
                self.system_status.set("🟢 系统运行正常 | 摄像头: 已连接 | 车牌识别: 进行中")

                # 启动摄像头显示线程 (UI线程调用)
                self.root.after(100, self.update_camera_display)

                # 启动识别处理线程
                self.start_recognition_processing()

                messagebox.showinfo("提示", "摄像头识别已启动，将实时检测车牌")
            else:
                messagebox.showerror("错误", "无法打开摄像头")

        except Exception as e:
            messagebox.showerror("错误", f"摄像头错误: {str(e)}")

    def start_recognition_processing(self):
        """ 启动识别处理线程 """
        if not self.is_camera_detecting:
            return

        self.camera_recognition_thread = threading.Thread(
            target=self.camera_recognition_worker,
            daemon=True
        )
        self.camera_recognition_thread.start()

    def camera_recognition_worker(self):
        """ 摄像头识别工作线程 - 使用myIdentify的process_source函数 """
        frame_count = 0
        temp_frame_path = "temp_camera_frame.jpg"
        temp_result_path = "temp_result.jpg"

        while self.is_camera_running and self.is_camera_detecting:
            if self.cap is None:
                time.sleep(0.1)
                continue

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            frame_count += 1

            # 每5帧处理一次，提高性能
            if frame_count % 5 != 0:
                continue

            try:
                # 保存临时帧用于识别
                cv2.imwrite(temp_frame_path, frame)

                # 使用myIdentify的process_source函数处理帧
                start_time = time.time()
                cropped_results = process_source(temp_frame_path, save_path=temp_result_path)
                processing_time = time.time() - start_time

                # 处理识别结果
                if cropped_results:
                    for plate_number, plate_image in cropped_results:
                        if plate_number and plate_number not in self.seen_plates:
                            self.seen_plates.add(plate_number)

                            # 存储识别结果，等待"开始识别"按钮点击
                            self.last_recognition_result = (plate_number, plate_image)
                            self.recognition_source_type = "camera"

                            # 在GUI线程中更新结果（只显示识别结果，不进行判断）
                            self.root.after(0, lambda pn=plate_number, pt=processing_time:
                            self.update_recognition_result(pn, pt))

                            # 保存车牌图像
                            self.save_detected_plate(plate_number, plate_image)

                # 如果有识别结果，显示带识别框的图像
                if os.path.exists(temp_result_path):
                    result_frame = cv2.imread(temp_result_path)
                    if result_frame is not None:
                        # 确保显示在 video_label (实时视频流区域)
                        self.root.after(0, lambda f=result_frame: self.update_detection_display(f))

            except Exception as e:
                print(f"识别处理错误: {e}")

            time.sleep(0.1)  # 控制识别频率

    def save_manual_input(self):
        """ 保存手动录入的车牌信息到数据库 """
        plate_number = self.manual_plate_number.get().strip()
        plate_type = self.manual_plate_type.get()

        if not plate_number:
            messagebox.showwarning("输入错误", "请输入车牌号码")
            return

        try:
            # 保存到数据库
            success = self.db_manager.add_authorized_plate(plate_number, plate_type, "手动录入")

            if success:
                info_text = f"车牌号码: {plate_number}\n车牌类型: {plate_type}\n状态: 已保存到数据库"
                messagebox.showinfo("保存成功", f"车牌信息已保存到数据库:\n\n{info_text}")
                self.system_status.set(f"🟢 手动录入成功 | 车牌: {plate_number} | 已保存到数据库")

                # 清空表单
                self.clear_manual_form()
            else:
                messagebox.showwarning("保存失败", f"车牌 {plate_number} 可能已存在或保存失败")

        except Exception as e:
            messagebox.showerror("保存错误", f"保存车牌信息时出错: {str(e)}")
            print(f"手动录入保存错误: {e}")

    def clear_manual_form(self):
        """ 清空手动录入表单 """
        self.manual_plate_number.set("")
        self.manual_plate_type.set("普通车牌")
        self.system_status.set("🟢 表单已清空")

    def open_barrier(self):
        """ 打开路障 - 发送控制指令到服务器 """
        try:
            # 发送打开路障指令
            # 假设协议：发送 "OPEN" 指令
            message = "OPEN".encode('utf-8')
            self.udp_socket.sendto(message, (self.udp_server_ip, self.udp_server_port))

            self.system_status.set("🟢 系统运行正常 | 路障状态: 已开启 | 注意安全")
            print(f"[UDP] 发送打开路障指令到 {self.udp_server_ip}:{self.udp_server_port}")
            messagebox.showinfo("控制", "路障已打开指令已发送")

        except Exception as e:
            error_msg = f"发送打开路障指令失败: {str(e)}"
            print(f"[UDP ERROR] {error_msg}")
            self.system_status.set(f"🔴 {error_msg}")
            messagebox.showerror("错误", error_msg)

    def close_barrier(self):
        try:
            message = "CLOSE".encode('utf-8')
            self.udp_socket.sendto(message, (self.udp_server_ip, self.udp_server_port))

            self.system_status.set("🟢 系统运行正常 | 路障状态: 已关闭")
            print(f"[UDP] 发送关闭路障指令到 {self.udp_server_ip}:{self.udp_server_port}")
            messagebox.showinfo("控制", "路障已关闭指令已发送")

        except Exception as e:
            error_msg = f"发送关闭路障指令失败: {str(e)}"
            print(f"[UDP ERROR] {error_msg}")
            self.system_status.set(f"🔴 {error_msg}")
            messagebox.showerror("错误", error_msg)

    def close_camera(self):
        """ 关闭相机和识别功能 """
        self.is_camera_running = False
        self.is_camera_detecting = False
        self.is_video_detecting = False

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        # 清理临时文件
        temp_files = ["temp_camera_frame.jpg", "temp_result.jpg"]
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

        self.video_label.config(image="",
                                text="🎥 视频流显示区域\n\n点击'打开相机识别'开始实时识别",
                                fg='#ecf0f1')
        self.system_status.set("🟢 系统运行正常 | 摄像头: 未连接 | 识别模型: 已加载")

        # 清空识别结果
        self.plate_number_var.set("")
        self.process_time_var.set("0.0秒")

    def detect_video(self):
        """ 检测视频 """
        if not self.is_camera_running and not self.current_video_path:
            messagebox.showwarning("警告", "请先打开摄像头或选择视频文件")
            return

        self.is_video_detecting = True
        self.system_status.set("🟡 系统运行正常 | 视频检测: 进行中")

        if self.current_video_path:
            messagebox.showinfo("提示", f"开始检测视频文件: {os.path.basename(self.current_video_path)}")
            # 实际的视频检测逻辑应在这里启动，可能是另一个线程
            # 暂时只做状态切换

        else:
            messagebox.showinfo("提示", "开始实时视频检测")

    def close_video(self):
        """ 关闭视频 """
        self.is_video_detecting = False
        self.stop_video_playback()  # 同时停止播放
        if self.is_camera_running:
            self.system_status.set("🟢 系统运行正常 | 摄像头: 已连接 | 视频检测: 已停止")
        else:
            self.system_status.set("🟢 系统运行正常 | 视频检测: 已停止")
        messagebox.showinfo("提示", "停止视频检测")

    def plate_input(self):
        """ 车牌录入 (调用图片选择) """
        self.select_image_file()

    def plate_view(self):
        """ 查看已选择的图片 """
        if self.selected_image_path:
            try:
                if os.path.exists(self.selected_image_path):
                    # 使用os.startfile(Windows) 或 os.system('open /path') (Mac) 或 os.system('xdg-open /path') (Linux)
                    if sys.platform.startswith('win'):
                        os.startfile(self.selected_image_path)
                    elif sys.platform.startswith('darwin'):  # Mac OS
                        os.system(f'open "{self.selected_image_path}"')
                    else:  # Linux
                        os.system(f'xdg-open "{self.selected_image_path}"')
                else:
                    messagebox.showerror("错误", "所选图片文件已被移动或删除")
                    self.selected_image_path = None  # 文件不存在时清空路径
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件: {str(e)}")
        else:
            messagebox.showinfo("提示", "请先选择一张图片")

    def clear_content(self):
        """ 清除内容 """
        self.image_label.config(image="", text="🖼️ 车辆图像将显示在这里\n\n请点击'选取图片'按钮加载图像", bg='white')
        self.plate_image_label.config(image="", text="🚗 校正后的车牌图像", bg='white')
        self.plate_number_var.set("")
        self.process_time_var.set("0.0秒")
        self.current_video_path = None
        self.video_preview_label.config(image="", text="🎥 车辆视频将显示在这里\n\n请点击'选取视频'按钮加载视频文件",
                                        bg='#2c3e50', fg='#ecf0f1')
        self.video_info_label.config(text="未选择视频文件", fg='#7f8c8d')
        self.video_label.config(image="", text="🎥 视频流显示区域\n\n点击'打开相机识别'开始实时识别", fg='#ecf0f1')
        self.seen_plates.clear()  # 清空已识别车牌记录
        self.stop_video_playback()  # 停止视频播放
        self.close_camera()  # 关闭相机/识别

    def resize_image_to_fit(self, image, max_width, max_height):
        """ 调整图像大小以适应显示区域 """
        h, w = image.shape[:2]

        # 如果显示区域大小未知，使用默认大小
        if max_width <= 1 or max_height <= 1:
            max_width, max_height = 400, 300

        # 计算缩放比例
        scale = min(max_width / w, max_height / h, 1)

        # 计算新尺寸
        new_w = int(w * scale)
        new_h = int(h * scale)

        # 调整图像大小
        resized = cv2.resize(image, (new_w, new_h))
        return resized

    def update_camera_display(self):
        """ 更新摄像头显示（原始帧）"""
        if not self.is_camera_running or self.cap is None:
            return

        ret, frame = self.cap.read()
        if ret:
            # 转换为RGB格式
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 调整图像大小以适应显示区域
            frame_rgb = self.resize_image_to_fit(frame_rgb,
                                                 self.video_container.winfo_width(),
                                                 self.video_container.winfo_height())

            # 转换为PIL图像然后转换为Tkinter图像
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)

            self.video_label.configure(image=imgtk, text="")
            self.video_label.image = imgtk

        # 继续更新显示
        if self.is_camera_running:
            self.root.after(30, self.update_camera_display)

    def update_detection_display(self, frame):
        """ 更新检测结果显示（带识别框的帧）"""
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = self.resize_image_to_fit(frame_rgb,
                                                     self.video_container.winfo_width(),
                                                     self.video_container.winfo_height())

            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)

            self.video_label.configure(image=imgtk, text="")
            self.video_label.image = imgtk
        except Exception as e:
            print(f"更新检测显示错误: {e}")

    def update_recognition_result(self, plate_number, processing_time):
        """ 更新识别结果到界面 """
        self.plate_number_var.set(plate_number)
        self.process_time_var.set(f"{processing_time:.2f}秒")

        # 更新状态提示
        self.system_status.set(f"🟢 识别到车牌: {plate_number} | 点击'开始识别'进行判断")

    def save_detected_plate(self, plate_number, plate_image):
        """ 保存检测到的车牌图像 """
        try:
            timestamp = int(time.time())
            filename = f"detected_plate_{plate_number}_{timestamp}.png"
            # 可以在这里保存文件，但为了避免磁盘操作过于频繁，仅更新显示
            # plate_image.save(filename)

            # 更新校正车牌图像显示
            self.root.after(0, lambda: self.update_plate_image_display(plate_image))

        except Exception as e:
            print(f"保存检测车牌错误: {e}")

    def update_plate_image_display(self, plate_image):
        """ 更新校正车牌图像显示 """
        try:
            # 调整图像大小
            plate_image.thumbnail((200, 100))
            imgtk = ImageTk.PhotoImage(plate_image)

            self.plate_image_label.configure(image=imgtk, text="")
            self.plate_image_label.image = imgtk

        except Exception as e:
            print(f"更新车牌图像显示错误: {e}")

    # --- 视频播放相关方法 ---

    def play_selected_video(self):
        """ 播放选中的视频文件 """
        if not self.current_video_path:
            messagebox.showwarning("警告", "请先选择视频文件")
            return

        if self.is_video_playing:
            return

        self.is_video_playing = True
        self.video_thread = threading.Thread(target=self._video_playback_worker, daemon=True)
        self.video_thread.start()

        self.video_info_label.config(
            text=f"播放中: {os.path.basename(self.current_video_path)}",
            fg='#27ae60'
        )

    def stop_video_playback(self):
        """ 停止视频播放 """
        self.is_video_playing = False
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None

        self.root.after(0, lambda: self.video_preview_label.config(
            image="",
            text="🎥 车辆视频将显示在这里\n\n请点击'选取视频'按钮加载视频文件"
        ))
        self.root.after(0, lambda: self.video_info_label.config(
            text="视频播放已停止",
            fg='#e74c3c'
        ))

    def _video_playback_worker(self):
        """ 视频播放工作线程 """
        try:
            self.video_cap = cv2.VideoCapture(self.current_video_path)
            cap = self.video_cap
            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("错误", "无法打开视频文件"))
                self.is_video_playing = False
                return

            # 获取视频属性
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0

            # 更新视频信息
            self.root.after(0, lambda: self.video_info_label.config(
                text=f"播放中: {os.path.basename(self.current_video_path)} | 时长: {duration:.1f}秒",
                fg='#27ae60'
            ))

            delay = int(1000 / fps) if fps > 0 else 30

            while self.is_video_playing and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    # 视频播放完毕，重新开始
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                # 在UI线程中更新显示
                self.root.after(0, lambda f=frame: self._update_video_frame(f))
                time.sleep(delay / 1000.0)

            cap.release()
            self.is_video_playing = False
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"视频播放错误: {str(e)}"))

    def _update_video_frame(self, frame):
        """ 更新视频帧显示 (左侧视频预览区域)"""
        try:
            # 获取显示区域的实际大小
            self.video_preview_label.update_idletasks()
            label_width = self.video_preview_label.winfo_width()
            label_height = self.video_preview_label.winfo_height()

            # 如果标签大小未知，使用默认大小
            if label_width <= 1 or label_height <= 1:
                label_width, label_height = 500, 300

            # 调整帧大小以适应显示区域
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]

            # 计算缩放比例，保持宽高比
            scale = min(label_width / w, label_height / h, 1.0)
            new_w = int(w * scale)
            new_h = int(h * scale)

            if new_w > 0 and new_h > 0:
                frame_resized = cv2.resize(frame_rgb, (new_w, new_h))

                # 转换为PIL图像然后转换为Tkinter图像
                img = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=img)

                self.video_preview_label.configure(image=imgtk)
                self.video_preview_label.image = imgtk

        except Exception as e:
            print(f"更新视频帧时出错: {e}")

    def show_video_viewer(self, filename):
        """ 显示视频文件的缩略图预览 """
        try:
            # 确保视频文件存在
            if not os.path.exists(filename):
                messagebox.showerror("错误", "视频文件不存在")
                return

            # 打开视频文件
            cap = cv2.VideoCapture(filename)
            if not cap.isOpened():
                messagebox.showerror("错误", "无法打开视频文件")
                return

            # 读取第一帧作为缩略图
            ret, frame = cap.read()
            cap.release()

            if not ret:
                self.video_preview_label.config(
                    text="无法读取视频帧",
                    bg='#2c3e50',
                    fg='#e74c3c'
                )
                return

            # 转换颜色空间 (OpenCV默认是BGR，需要转为RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 获取显示区域的大小
            self.video_preview_label.update_idletasks()
            label_width = self.video_preview_label.winfo_width()
            label_height = self.video_preview_label.winfo_height()

            if label_width <= 1 or label_height <= 1:
                label_width, label_height = 400, 250

            # 调整图像大小以适应显示区域
            h, w = frame_rgb.shape[:2]
            scale = min(label_width / w, label_height / h, 1.0)
            new_w = int(w * scale)
            new_h = int(h * scale)

            if new_w > 0 and new_h > 0:
                frame_resized = cv2.resize(frame_rgb, (new_w, new_h))

                pil_image = Image.fromarray(frame_resized)
                tk_image = ImageTk.PhotoImage(image=pil_image)

                self.video_preview_label.configure(
                    image=tk_image,
                    text="",
                    bg='#2c3e50'
                )
                self.video_preview_label.image = tk_image

                # 更新视频信息
                video_name = os.path.basename(filename)
                file_size = os.path.getsize(filename) / (1024 * 1024)  # 转换为MB
                self.video_info_label.config(
                    text=f"已选择: {video_name} | 大小: {file_size:.1f}MB",
                    fg='#3498db'
                )

            else:
                self.video_preview_label.config(
                    text="视频帧尺寸异常",
                    bg='#2c3e50',
                    fg='#e74c3c'
                )

        except Exception as e:
            self.video_preview_label.config(
                text=f"加载视频失败: {str(e)}",
                bg='#2c3e50',
                fg='#e74c3c'
            )
            self.video_info_label.config(
                text="视频加载失败",
                fg='#e74c3c'
            )
            print(f"show_video_viewer error: {e}")


def send_plate_status_to_udp_server(self, plate_number, is_authorized):
    """
    构建 UDP 协议数据包
    - 授权时: 发送状态 0
    - 未授权时: 发送状态 1
    """
    if not self.udp_socket:
        print("[UDP] 警告: UDP 客户端未初始化，无法发送数据。")
        return

    try:
        # 1. 解析车牌
        chinese_char = plate_number[0]
        rest_plate = plate_number[1:]

        # 2. 获取汉字索引
        chinese_index = self.CHINESE_PLATE_MAPPING.get(chinese_char)
        if chinese_index is None:
            print(f"[UDP] 错误: 未知汉字 '{chinese_char}'，无法发送。")
            return

        # 3. 根据授权状态设置状态位
        # 授权通过发0，未授权通过发1
        status_byte = 0 if is_authorized else 1
        status_msg = "授权通过" if is_authorized else "未授权拒绝"

        # 4. 格式化车牌剩余部分 (7字节 ASCII)
        formatted_rest = rest_plate.ljust(7, ' ')[:7]
        plate_bytes = formatted_rest.encode('ascii')

        if len(plate_bytes) != 7:
            print(f"[UDP] 格式错误: 车牌剩余部分长度不为7: {len(plate_bytes)}")
            return

        # 5. 构建 9 字节数据包
        # 结构: [1字节汉字索引] + [7字节车牌剩余部分] + [1字节状态位]
        car_data = bytes([chinese_index]) + plate_bytes + bytes([status_byte])

        print(f"[UDP] 发送 9 字节数据: {list(car_data)}")
        print(
            f"      数据内容: 汉字索引={chinese_index}, 车牌='{chinese_char}{rest_plate}', 状态={status_byte}({status_msg})")

        # 6. 发送数据
        self.udp_socket.sendto(car_data, (self.udp_server_ip, self.udp_server_port))

        print(f"[UDP] 成功发送数据到服务器: {self.udp_server_ip}:{self.udp_server_port}")
        print(f"      状态: {status_msg}")

    except Exception as e:
        print(f"[UDP ERROR] 发送数据失败: {e}")
        self.root.after(0, lambda: messagebox.showerror("UDP错误", f"发送 UDP 数据失败: {e}"))