import queue
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import cv2
import os
import socket

from plate_utils import calculate_runtime
from plate_recognition import process_source

from gui_styles import GUIStyles
from gui_handlers import GUIHandlers, DatabaseManager
from gui_styles import GUIStyles
from gui_handlers import GUIHandlers, DatabaseManager


class LicensePlateRecognitionSystem(GUIStyles, GUIHandlers):
    """
    基于深度学习的车牌识别系统主应用类。
    继承 GUIStyles 处理样式和界面创建。
    继承 GUIHandlers 处理事件和业务逻辑。
    """

    def __init__(self, root):
        self.root = root
        self.root.title("基于深度学习的车牌识别系统")
        self.root.geometry("1250x780")
        self.root.configure(bg='#f8f9fa')

        self.selected_image_path = None

        # 摄像头相关变量
        self.cap = None
        self.is_camera_running = False
        self.is_camera_detecting = False
        self.seen_plates = set()  # 记录已识别的车牌，避免重复提示
        self.frame_queue = queue.Queue(maxsize=5)  # 用于处理识别的帧队列

        # 视频相关变量
        self.current_video_path = None  # 当前视频文件路径
        self.video_cap = None
        self.is_video_playing = False
        self.is_video_detecting = False
        self.video_thread = None

        # 识别结果存储变量
        self.last_recognition_result = None  # 存储最后一次识别结果 (plate_number, plate_image)
        self.recognition_source_type = None  # 识别来源类型 (file/camera)

        # UDP 通信配置
        self.udp_server_ip = "127.0.0.1"
        self.udp_server_port = 9001
        self.udp_socket = None

        # 界面控件变量 (初始化为None，在 create_widgets 中赋值)
        self.image_label = None
        self.video_preview_label = None
        self.video_info_label = None
        self.manual_plate_number = tk.StringVar()
        self.manual_plate_type = tk.StringVar(value="普通车牌")
        self.plate_image_label = None
        self.detect_algo_var = tk.StringVar(value="YOLOv8")
        self.recognize_algo_var = tk.StringVar(value="CRNN")
        self.plate_type_var = tk.StringVar(value="普通车牌")
        self.plate_number_var = tk.StringVar(value="")
        self.process_time_var = tk.StringVar(value="0.0秒")
        self.video_container = None
        self.video_label = None
        self.system_status = tk.StringVar(value="🟢 系统运行正常 | 摄像头: 未连接 | 识别模型: 已加载")

        # 初始化 UI 和 UDP 客户端
        self.setup_styles()
        self.create_widgets()
        self.init_udp_client()

        self.db_manager = DatabaseManager()