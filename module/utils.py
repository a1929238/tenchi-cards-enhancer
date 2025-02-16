# 常用方法
import json
from ctypes import windll

import numpy as np
import cv2
import sys
import os

import win32gui

from module.globals import GLOBALS
from module.log.TenchiLogger import logger


# 读取图片
def imread(filename, with_alpha=False):
    """将图片读取为np数组"""
    # 使用 np.fromfile 读取数据
    data = np.fromfile(filename, dtype=np.uint8)
    # 使用 cv2.imdecode() 解码图像数据
    if with_alpha:
        image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    else:
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return image


def imread_to_hash(filename):
    """
    读取图片的哈希值，用于快速比对图片是否相同。
    """
    # 使用 np.fromfile 读取数据
    data = np.fromfile(filename, dtype=np.uint8)
    # 使用 cv2.imdecode() 解码图像数据
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return hash(image.tobytes())


def get_system_dpi():
    """
    获取当前系统的DPI设置。
    """
    # 创建一个设备上下文（DC）用于屏幕
    hdc = windll.user32.GetDC(0)
    # 获取屏幕的水平DPI
    dpi = windll.gdi32.GetDeviceCaps(hdc, 88)  # 88 is the index for LOGPIXELSX
    windll.user32.ReleaseDC(0, hdc)
    return dpi


# 打包后绝对路径函数
def resource_path(relative_path: str):
    """获取项目根目录下的资源文件的绝对路径。"""
    # 如果打包，则使用 PyInstaller 的临时目录
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        # 如果未打包，则使用当前文件的目录
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path).replace('\\', '/')


def hide_row_widgets(layout, row):
    """
    隐藏栅格布局中，指定行中的所有控件。

    Args:
        layout: QGridLayout 对象。
        row: 要隐藏的行号 (从0开始计数)。
    """
    for i in range(layout.columnCount()):
        item = layout.itemAtPosition(row, i)
        if item is not None:
            widget = item.widget()
            if widget is not None:
                widget.hide()


def show_row_widgets(layout, row):
    """
    显示栅格布局中，指定行中的所有控件。
    Args:
        layout: QGridLayout 对象。
        row: 要显示的行号 (从0开始计数)。
    """
    for i in range(layout.columnCount()):
        item = layout.itemAtPosition(row, i)
        if item is not None:
            widget = item.widget()
            if widget is not None:
                widget.show()


def template_match_with_mask(img, tar_img, extra_mask=None):
    # 图片带有透明度通道，先将透明度部分转化为掩码
    mask = tar_img[:, :, 3]
    # 叠加上基础掩码
    if extra_mask is not None:
        extra_mask = extra_mask[:, :, 0]
        mask = cv2.bitwise_and(mask, extra_mask)
    # 再只取前三个通道
    img = img[:, :, :3]
    tar_img = tar_img[:, :, :3]
    result = cv2.matchTemplate(img, tar_img, cv2.TM_CCORR_NORMED, mask=mask)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= 0.99:
        return True
    else:
        return False


def load_settings(filename='setting.json'):
    """
    从JSON文件中读取设置，再与默认设置比对和补缺，还有老设置更新功能
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            # 与默认字典比对，如果缺少了默认字典的键，则把默认字典的键添加进去
            settings = json.load(f)
        filename = resource_path('GUI/default/setting.json')
        with open(filename, 'r', encoding='utf-8') as f:
            default = json.load(f)
        for key, value in default.items():
            if key not in settings:
                settings[key] = value
            if key == "个人设置":
                for k, v in value.items():
                    if k not in settings["个人设置"]:
                        settings["个人设置"][k] = v
        return settings  # 返回设置字典
    except FileNotFoundError:
        filename = resource_path('GUI/default/setting.json')
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)  # 返回默认字典，如果设置文件不存在


def merge_card_counts(list1, list2):
    count_dict = {}
    for lst in (list1, list2):
        for card, cnt in lst:
            count_dict[card] = count_dict.get(card, 0) + cnt
    return [(card, count) for card, count in count_dict.items()]


def load_level_crystal_map():
    """
    读取宝石等级和消耗水晶的映射表
    """
    filename = resource_path('GUI/default/level_crystal_map.json')
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_statistics(statistics, filename='statistics.json'):
    """
    保存统计数据
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(statistics, f, ensure_ascii=False, indent=4)


def save_settings(settings, filename='setting.json'):
    """
    保存设置
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def handle_check(handle):
    """
    根据窗口类名，窗口大小，校验该窗口是否为flash游戏窗口
    """
    # 窗口名
    window_name = win32gui.GetWindowText(handle)
    # 窗口类名
    window_class_name = win32gui.GetClassName(handle)
    # 窗口大小
    window_rect = win32gui.GetWindowRect(handle)
    left, top, right, bottom = window_rect
    width = right - left
    height = bottom - top

    scale = GLOBALS.DPI / 96
    # 计算期望的窗口尺寸
    expected_width = int(950 * scale)
    expected_height = int(596 * scale)

    logger.info(handle, window_name, window_class_name, width, height)

    # 允许1个像素内的误差
    if abs(width - expected_width) <= 1 and abs(height - expected_height) <= 1:
        return True


def find_sibling_window_by_class(hwnd, sibling_class_name):
    parent = win32gui.GetParent(hwnd)
    if not parent:
        return None

    hwnd_sibling = None

    def enum_sibling_windows(hwnd, param):
        nonlocal hwnd_sibling
        if win32gui.GetClassName(hwnd) == sibling_class_name:
            hwnd_sibling = hwnd
            return False  # 停止枚举
        return True  # 继续枚举

    win32gui.EnumChildWindows(parent, enum_sibling_windows, None)
    return hwnd_sibling
