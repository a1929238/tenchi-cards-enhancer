import cProfile

import cv2
import numpy as np
import win32gui

import module.globals.GLOBALS as GLOBALS
from module.core.DynamicWait import dynamic_wait_card_slot_state
from module.core.GetImg import get_image
from module.core.ItemTab import get_item_list
from module.core.LevelCheck import check_gem_enhance_result
from module.globals.ResourceInit import resource
from module.ocr.NumberOcr import get_num
from module.ocr.SuccessRateOcr import get_success_rate
from module.utils import template_match_with_mask, imread, resource_path


def img_save(img, filename):
    cv2.imwrite(filename, img)


def get_pixel_position(x, y):
    """
    获取鼠标点击位置相对于目标句柄窗口的位置
    :param x: 鼠标点击位置的x坐标
    :param y: 鼠标点击位置的y坐标
    """
    # 获取窗口的坐标
    window_left, window_top, _, _ = win32gui.GetWindowRect(GLOBALS.HWND)

    # 计算鼠标相对于窗口的坐标
    relative_x = x - window_left
    relative_y = y - window_top

    return relative_x, relative_y


def test():
    img = imread(resource_path("test.png"))
    result = get_num(img)
    print(result)


def test_get_item_list():
    item_list = get_item_list("香料")
    for item in item_list:
        item.print()
