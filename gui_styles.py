import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk


class GUIStyles:
    """ 负责设置现代化样式和创建所有界面组件 """

    def setup_styles(self):
        """设置现代化控件样式"""
        style = ttk.Style()
        style.theme_use('clam')

        # 配置主色调
        style.configure('Title.TLabel',
                        font=('微软雅黑', 18, 'bold'),
                        background='#f8f9fa',
                        foreground='#2c3e50')

        # 主操作按钮
        style.configure('Primary.TButton',
                        font=('微软雅黑', 11),
                        foreground="white",
                        background="#3498db",
                        focuscolor='none',
                        borderwidth=2,
                        relief="flat",
                        padding=(15, 8))
        style.map('Primary.TButton',
                  background=[('active', '#2980b9'), ('!active', '#3498db')])

        # 成功状态按钮
        style.configure('Success.TButton',
                        font=('微软雅黑', 11),
                        foreground="white",
                        background="#27ae60",
                        focuscolor='none',
                        borderwidth=2,
                        relief="flat",
                        padding=(15, 8))
        style.map('Success.TButton',
                  background=[('active', '#219653'), ('!active', '#27ae60')])

        # 次要操作按钮
        style.configure('Secondary.TButton',
                        font=('微软雅黑', 11),
                        foreground="white",
                        background="#95a5a6",
                        focuscolor='none',
                        borderwidth=2,
                        relief="flat",
                        padding=(15, 8))
        style.map('Secondary.TButton',
                  background=[('active', '#7f8c8d'), ('!active', '#95a5a6')])

        # 框架样式
        style.configure('Custom.TLabelframe',
                        background='#f8f9fa',
                        bordercolor='#dee2e6',
                        relief='flat',
                        borderwidth=1)
        style.configure('Custom.TLabelframe.Label',
                        font=('微软雅黑', 12, 'bold'),
                        background='#f8f9fa',
                        foreground='#2c3e50')

        # 下拉框样式
        style.configure('Custom.TCombobox',
                        fieldbackground='white',
                        background='white',
                        borderwidth=1,
                        relief='solid')

    def create_widgets(self):
        """ 创建现代化界面组件 - 布局和调用子组件创建函数 """
        # 标题区域 - 现代化设计
        title_frame = tk.Frame(self.root, bg='#3498db', height=100, relief='flat')
        title_frame.pack(fill='x', padx=0, pady=0)
        title_frame.pack_propagate(False)

        # 标题文本和副标题
        title_container = tk.Frame(title_frame, bg='#3498db')
        title_container.pack(expand=True, fill='both', padx=30, pady=15)

        title_label = tk.Label(title_container,
                               text="基于深度学习的车牌识别系统",
                               font=('微软雅黑', 22, 'bold'),
                               bg='#3498db',
                               fg='white')
        title_label.pack(pady=(5, 0))

        subtitle_label = tk.Label(title_container,
                                  text="智能车牌检测与识别解决方案",
                                  font=('微软雅黑', 11),
                                  bg='#3498db',
                                  fg='#e8f4f8')
        subtitle_label.pack(pady=(0, 5))

        # 控制按钮区域 - 卡片式设计
        self.create_control_panel()

        # 主内容区域
        main_frame = tk.Frame(self.root, bg='#f8f9fa')
        main_frame.pack(fill='both', expand=True, padx=25, pady=20)

        # 三列布局
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=2)
        main_frame.columnconfigure(2, weight=3)
        main_frame.rowconfigure(0, weight=1)

        # 左侧区域 - 读入车辆图像
        self.create_left_section(main_frame)

        # 中间区域 - 新增车牌手动录入，原校正车牌图像区域下移
        self.create_center_section(main_frame)

        # 右侧区域 - 识别结果和视频
        self.create_right_section(main_frame)

        # 底部状态栏
        self.create_status_bar()

    def create_control_panel(self):
        """ 创建控制按钮面板 """
        control_frame = tk.Frame(self.root, bg='#ffffff', height=70, relief='flat', bd=1)
        control_frame.pack(fill='x', padx=25, pady=15)
        control_frame.pack_propagate(False)

        # 控制面板内部框架
        inner_control_frame = tk.Frame(control_frame, bg='#ffffff')
        inner_control_frame.pack(expand=True, fill='both', padx=25, pady=15)

        # 文件操作区域
        file_control_frame = tk.Frame(inner_control_frame, bg='#ffffff')
        file_control_frame.pack(side='left', padx=10)

        ttk.Button(file_control_frame, text="🖼️ 选取图片",
                   command=self.select_image_file,
                   style='Primary.TButton',
                   width=12).pack(side='left', padx=3)

        ttk.Button(file_control_frame, text="🎥 选取视频",
                   command=self.select_video_file,
                   style='Primary.TButton',
                   width=12).pack(side='left', padx=3)

        ttk.Button(file_control_frame, text="🔍 开始识别",
                   command=self.start_recognition,
                   style='Success.TButton',
                   width=12).pack(side='left', padx=3)

        ttk.Button(file_control_frame, text="🗑️ 清除内容",
                   command=self.clear_content,
                   style='Secondary.TButton',
                   width=12).pack(side='left', padx=3)

        # 设备控制区域
        device_control_frame = tk.Frame(inner_control_frame, bg='#ffffff')
        device_control_frame.pack(side='right', padx=10)

        # 路障控制
        ttk.Button(device_control_frame, text="🚧 打开路障",
                   command=self.open_barrier,
                   style='Success.TButton',
                   width=10).pack(side='left', padx=2)

        ttk.Button(device_control_frame, text="🚧 关闭路障",
                   command=self.close_barrier,
                   style='Secondary.TButton',
                   width=10).pack(side='left', padx=2)

        # 修改相机控制按钮 - 增加识别功能
        ttk.Button(device_control_frame, text="📷 打开相机识别",  # 修改按钮文本
                   command=self.open_camera_with_recognition,  # 修改为新的识别方法
                   style='Success.TButton',
                   width=12).pack(side='left', padx=2)

        ttk.Button(device_control_frame, text="📷 关闭相机",
                   command=self.close_camera,
                   style='Secondary.TButton',
                   width=10).pack(side='left', padx=2)

        # 视频控制
        ttk.Button(device_control_frame, text="🎥 检测视频",
                   command=self.detect_video,
                   style='Success.TButton',
                   width=10).pack(side='left', padx=2)

        ttk.Button(device_control_frame, text="🎥 关闭视频",
                   command=self.close_video,
                   style='Secondary.TButton',
                   width=10).pack(side='left', padx=2)

    def create_left_section(self, parent):
        """ 创建左侧区域 - 读入车辆图像 """
        left_frame = ttk.LabelFrame(parent, text="📸 读入车辆图像", padding=20, style='Custom.TLabelframe')
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 15))

        # 车牌管理按钮区域
        plate_management_frame = tk.Frame(left_frame, bg='#f8f9fa')
        plate_management_frame.pack(fill='x', pady=(0, 15))

        ttk.Button(plate_management_frame, text="📝 车牌录入",
                   command=self.plate_input,
                   style='Primary.TButton',
                   width=12).pack(side='left', padx=(0, 10))

        ttk.Button(plate_management_frame, text="👀 车牌查看",
                   command=self.plate_view,
                   style='Primary.TButton',
                   width=12).pack(side='left')

        # 图像显示区域
        image_container = tk.Frame(left_frame, bg='#ffffff', relief='solid', bd=1)
        image_container.pack(fill='both', expand=True, pady=10)

        self.image_label = tk.Label(image_container,
                                    text="🖼️ 车辆图像将显示在这里\n\n请点击'选取图片'按钮加载图像",
                                    bg='#ffffff',
                                    fg='#6c757d',
                                    font=('微软雅黑', 11),
                                    justify='center',
                                    padx=20,
                                    pady=40)
        self.image_label.pack(expand=True, fill='both')

        self.create_video_section(left_frame)

    def create_video_section(self, parent):
        """ 创建读入车辆视频模块 """
        # 视频模块框架
        video_section_frame = ttk.LabelFrame(parent, text="🎥 读入车辆视频", padding=15, style='Custom.TLabelframe')
        video_section_frame.pack(fill='both', expand=True, pady=(20, 0))

        # 视频控制按钮区域
        video_control_frame = tk.Frame(video_section_frame, bg='#f8f9fa')
        video_control_frame.pack(fill='x', pady=(0, 10))

        ttk.Button(video_control_frame, text="⏵ 播放视频",
                   command=self.play_selected_video,
                   style='Success.TButton',
                   width=12).pack(side='left', padx=5)

        ttk.Button(video_control_frame, text="⏹ 停止视频",
                   command=self.stop_video_playback,
                   style='Secondary.TButton',
                   width=12).pack(side='left', padx=5)

        # 视频显示区域
        video_container = tk.Frame(video_section_frame, bg='#2c3e50', relief='solid', bd=1, height=200)
        video_container.pack(fill='both', expand=True, pady=10)
        video_container.pack_propagate(False)

        self.video_preview_label = tk.Label(video_container,
                                            text="🎥 车辆视频将显示在这里\n\n请点击'选取视频'按钮加载视频文件",
                                            bg='#2c3e50',
                                            fg='#ecf0f1',
                                            font=('微软雅黑', 10),
                                            justify='center',
                                            pady=60)
        self.video_preview_label.pack(expand=True, fill='both')

        # 视频信息显示
        self.video_info_label = tk.Label(video_section_frame,
                                         text="未选择视频文件",
                                         bg='#f8f9fa',
                                         fg='#7f8c8d',
                                         font=('微软雅黑', 9))
        self.video_info_label.pack(fill='x')

    def create_center_section(self, parent):
        """ 创建中间区域 """
        center_frame = ttk.LabelFrame(parent, text="📋 车牌手动录入", padding=20, style='Custom.TLabelframe')
        center_frame.grid(row=0, column=1, sticky='nsew', padx=15)

        # 车牌手动录入表单
        form_frame = tk.Frame(center_frame, bg='#f8f9fa')
        form_frame.pack(fill='x', pady=(0, 15))

        # 车牌号码输入
        plate_number_frame = tk.Frame(form_frame, bg='#f8f9fa')
        plate_number_frame.pack(fill='x', pady=8)

        tk.Label(plate_number_frame, text="车牌号码:",
                 font=('微软雅黑', 10, 'bold'),
                 bg='#f8f9fa',
                 fg='#495057').pack(side='left', anchor='w')

        plate_entry = ttk.Entry(plate_number_frame,
                                textvariable=self.manual_plate_number,
                                font=('微软雅黑', 10),
                                width=15)
        plate_entry.pack(side='right', fill='x', expand=True, padx=(10, 0))

        # 车牌类型选择
        plate_type_frame = tk.Frame(form_frame, bg='#f8f9fa')
        plate_type_frame.pack(fill='x', pady=8)

        tk.Label(plate_type_frame, text="车牌类型:",
                 font=('微软雅黑', 10, 'bold'),
                 bg='#f8f9fa',
                 fg='#495057').pack(side='left', anchor='w')

        type_combo = ttk.Combobox(plate_type_frame,
                                  textvariable=self.manual_plate_type,
                                  values=["普通车牌", "新能源车牌", "军用车牌", "警用车牌", "使馆车牌", "其他"],
                                  state="readonly",
                                  width=12)
        type_combo.pack(side='right')

        # 按钮区域
        button_frame = tk.Frame(form_frame, bg='#f8f9fa')
        button_frame.pack(fill='x', pady=(15, 5))

        ttk.Button(button_frame, text="💾 保存录入",
                   command=self.save_manual_input,
                   style='Success.TButton',
                   width=12).pack(side='left', padx=(0, 10))

        ttk.Button(button_frame, text="🔄 清空表单",
                   command=self.clear_manual_form,
                   style='Secondary.TButton',
                   width=12).pack(side='left')

        correction_frame = ttk.LabelFrame(parent, text="🔄 校正车牌图像", padding=20, style='Custom.TLabelframe')
        correction_frame.grid(row=1, column=1, sticky='nsew', padx=15, pady=(20, 0))

        # 调整行权重，使两个区域都能合理分布空间
        parent.rowconfigure(1, weight=1)

        # 车牌图像显示区域
        plate_image_container = tk.Frame(correction_frame, bg='#ffffff', relief='solid', bd=1, height=140)
        plate_image_container.pack(fill='x', pady=(0, 20))
        plate_image_container.pack_propagate(False)

        self.plate_image_label = tk.Label(plate_image_container,
                                          text="🚗 校正后的车牌图像",
                                          bg='#ffffff',
                                          fg='#6c757d',
                                          font=('微软雅黑', 11))
        self.plate_image_label.pack(expand=True)

        # 算法选择区域
        algorithm_frame = tk.Frame(correction_frame, bg='#f8f9fa')
        algorithm_frame.pack(fill='x', pady=10)

        # 车牌检测算法
        detect_algo_frame = tk.Frame(algorithm_frame, bg='#f8f9fa')
        detect_algo_frame.pack(fill='x', pady=8)

        tk.Label(detect_algo_frame, text="检测算法:",
                 font=('微软雅黑', 10, 'bold'),
                 bg='#f8f9fa',
                 fg='#495057').pack(side='left')

        detect_combo = ttk.Combobox(detect_algo_frame,
                                    textvariable=self.detect_algo_var,
                                    values=["YOLOv5", "YOLOv7", "YOLOv8", "Faster R-CNN"],
                                    state="readonly",
                                    width=15)
        detect_combo.pack(side='right')

        # 车牌识别算法
        recognize_algo_frame = tk.Frame(algorithm_frame, bg='#f8f9fa')
        recognize_algo_frame.pack(fill='x', pady=8)

        tk.Label(recognize_algo_frame, text="识别算法:",
                 font=('微软雅黑', 10, 'bold'),
                 bg='#f8f9fa',
                 fg='#495057').pack(side='left')

        recognize_combo = ttk.Combobox(recognize_algo_frame,
                                       textvariable=self.recognize_algo_var,
                                       values=["CRNN", "LPRNet", "CNN+LSTM"],
                                       state="readonly",
                                       width=15)
        recognize_combo.pack(side='right')

    def create_right_section(self, parent):
        """创建右侧区域 - 识别结果和视频图像"""
        right_frame = tk.Frame(parent, bg='#f8f9fa')
        right_frame.grid(row=0, column=2, rowspan=2, sticky='nsew', padx=(15, 0))  # 扩展为两行

        # 识别结果区域
        result_frame = ttk.LabelFrame(right_frame, text="✅ 识别结果", padding=20, style='Custom.TLabelframe')
        result_frame.pack(fill='x', pady=(0, 20))

        # 车牌种类
        plate_type_frame = tk.Frame(result_frame, bg='#f8f9fa')
        plate_type_frame.pack(fill='x', pady=8)

        tk.Label(plate_type_frame, text="车牌种类:",
                 font=('微软雅黑', 10, 'bold'),
                 bg='#f8f9fa',
                 fg='#495057').pack(side='left')

        plate_type_combo = ttk.Combobox(plate_type_frame,
                                        textvariable=self.plate_type_var,
                                        values=["普通车牌", "新能源车牌", "军用车牌", "警用车牌"],
                                        state="readonly",
                                        width=12)
        plate_type_combo.pack(side='right')

        # 识别车牌号码
        plate_number_frame = tk.Frame(result_frame, bg='#f8f9fa')
        plate_number_frame.pack(fill='x', pady=12)

        tk.Label(plate_number_frame, text="识别号码:",
                 font=('微软雅黑', 10, 'bold'),
                 bg='#f8f9fa',
                 fg='#495057').pack(side='left')

        plate_number_label = tk.Label(plate_number_frame,
                                      textvariable=self.plate_number_var,
                                      font=('Arial', 18, 'bold'),
                                      bg='#ffeaa7',
                                      fg='#d35400',
                                      relief='solid',
                                      bd=1,
                                      width=14,
                                      padx=10,
                                      pady=8)
        plate_number_label.pack(side='right')

        # 处理时间
        process_time_frame = tk.Frame(result_frame, bg='#f8f9fa')
        process_time_frame.pack(fill='x', pady=8)

        tk.Label(process_time_frame, text="处理时间:",
                 font=('微软雅黑', 10, 'bold'),
                 bg='#f8f9fa',
                 fg='#495057').pack(side='left')

        time_label = tk.Label(process_time_frame,
                              textvariable=self.process_time_var,
                              font=('微软雅黑', 10, 'bold'),
                              bg='#f8f9fa',
                              fg='#3498db')
        time_label.pack(side='right')

        # 视频图像区域
        video_frame = ttk.LabelFrame(right_frame, text="📹 实时视频流", padding=20, style='Custom.TLabelframe')
        video_frame.pack(fill='both', expand=True)

        # 视频显示区域
        self.video_container = tk.Frame(video_frame, bg='#2c3e50', relief='solid', bd=1)
        self.video_container.pack(fill='both', expand=True)

        self.video_label = tk.Label(self.video_container,
                                    text="🎥 视频流显示区域\n\n点击'打开相机识别'开始实时识别",  # 文本修改以匹配按钮
                                    bg='#2c3e50',
                                    fg='#ecf0f1',
                                    font=('微软雅黑', 11),
                                    justify='center',
                                    pady=40)
        self.video_label.pack(expand=True)

    def create_status_bar(self):
        """ 创建底部状态栏 """
        status_frame = tk.Frame(self.root, bg='#34495e', height=40)
        status_frame.pack(fill='x', side='bottom')
        status_frame.pack_propagate(False)

        # 状态信息
        status_container = tk.Frame(status_frame, bg='#34495e')
        status_container.pack(expand=True, fill='both', padx=25)

        # 系统状态
        status_label = tk.Label(status_container,
                                textvariable=self.system_status,
                                font=('微软雅黑', 9),
                                bg='#34495e',
                                fg='#2ecc71')
        status_label.pack(side='left')

        # 版权信息
        copyright_label = tk.Label(status_container,
                                   text="© 2025 智能车牌识别系统 v2.0",
                                   font=('微软雅黑', 9),
                                   bg='#34495e',
                                   fg='#bdc3c7')
        copyright_label.pack(side='right')