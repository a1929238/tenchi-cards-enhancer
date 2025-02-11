import cv2
import win32gui

import module.globals.GLOBALS as GLOBALS
from module.core.ItemTab import get_item_list
from module.core.PositionCheck import check_position


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
    position = check_position()
    print(position)


def test_get_item_list():
    item_list = get_item_list("香料")
    for item in item_list:
        item.print()
