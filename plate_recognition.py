import cv2
import hyperlpr3 as lpr3
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import sys
import time

# -------------------------------
# 识别函数
# -------------------------------
def recognize_frame(frame):
    """
    识别传入的 OpenCV 矩阵中的车牌
    输入: frame (np.ndarray)
    输出: [(plate_number, box), ...]
    """
    lpr = lpr3.LicensePlateCatcher()
    results = lpr(frame)
    return [(code, box) for code, conf, type_idx, box in results]


# -------------------------------
# 绘制函数
# -------------------------------
def draw_frame(frame, results):
    """
    在矩阵上绘制车牌框和车牌号
    输入: frame (np.ndarray), results [(plate_number, box), ...]
    输出: 绘制后的矩阵 (np.ndarray)
    """
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)

    # ---- 字体路径自动选择（兼容 Win + Linux） ----
    font = None
    font_paths = []

    if sys.platform.startswith("win"):
        font_paths = [
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\arial.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/arphic/ukai.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 22)
                print(f"[信息] 成功加载字体: {fp}")
                break
            except Exception as e:
                print(f"[警告] 字体加载失败 {fp}: {e}")

    if font is None:
        font = ImageFont.load_default()
        print("[警告] 使用默认字体 (不支持中文)")

    # ---- 绘制检测框 ----
    for code, box in results:
        x1, y1, x2, y2 = map(int, box)
        draw.rectangle([x1, y1, x2, y2], outline="lime", width=3)
        draw.text((x1, max(y1 - 25, 0)), code, fill="lime", font=font)

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# -------------------------------
# 裁剪车牌函数
# -------------------------------
def crop_plates(frame, results):
    """
    裁剪出车牌区域
    输出: List[(plate_number, PIL.Image)]
    """
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    cropped_list = []
    for code, box in results:
        x1, y1, x2, y2 = map(int, box)
        cropped = pil_img.crop((x1, y1, x2, y2))
        cropped_list.append((code, cropped))
    return cropped_list


# -------------------------------
# 通用处理函数
# -------------------------------
def process_source(source, save_path="res.png", frame_skip=5):
    """
    处理图片/视频/摄像头
    输入:
        source: str(图像/视频路径) 或 int(摄像头索引)
        save_path: str 输出路径
    输出: List[(plate_number, PIL.Image裁剪图)]
    """

    # -------- 图片模式 --------
    if isinstance(source, str) and os.path.isfile(source):
        ext = os.path.splitext(source)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            img = cv2.imread(source)
            if img is None:
                print("[错误] 无法读取图片:", source)
                return []
            results = recognize_frame(img)
            if not results:
                return []
            out_img = draw_frame(img, results)
            cv2.imwrite(save_path, out_img)
            cropped = crop_plates(img, results)

            return cropped

    # -------- 摄像头 / 视频模式 --------

    if isinstance(source, int):
        if sys.platform.startswith("win"):
            cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(source)
    else:
        cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print("[错误] 无法打开视频/摄像头:", source)
        return []


    seen_plates = set()
    frame_count = 0
    cropped_results = []

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[提示] 视频结束")
            break

        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        results = recognize_frame(frame)
        if results:
            new_results = [(c, b) for c, b in results if c not in seen_plates]
            for code, _ in new_results:
                seen_plates.add(code)
                print(f"[识别到新车牌] {code}")

            if new_results:
                out_img = draw_frame(frame, new_results)
                cv2.imwrite(save_path, out_img)
                cropped_results.extend(crop_plates(frame, new_results))

    cap.release()
    cv2.destroyAllWindows()
    return cropped_results
