import win32api
import win32gui
import win32con
import module.globals.GLOBALS as GLOBALS


def click(x, y, handle=None):
    """点击指定位置
    Args:
        x (int): x坐标
        y (int): y坐标
        handle (int, optional): 句柄. Defaults to None.
    """
    # 默认使用flash句柄
    if not handle:
        handle = GLOBALS.HWND
    # 获取系统缩放比例（默认DPI是96）
    scale_factor = GLOBALS.DPI / 96.0
    # 调整坐标
    scaled_x = int(x * scale_factor)
    scaled_y = int(y * scale_factor)
    # 将x和y转化成矩阵
    lParam = win32api.MAKELONG(scaled_x, scaled_y)
    # 发送一次鼠标左键单击
    win32gui.PostMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    win32gui.PostMessage(handle, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lParam)


# 拖曳,x1y1为需要拖曳的距离
def drag(x, y, x1, y1, handle=None):
    """拖曳指定位置
    Args:
        x (int): x坐标
        y (int): y坐标
        x1 (int): 需要移动的x距离
        y1 (int): 需要移动的y距离
        handle (int, optional): 句柄. Defaults to None.
    """
    if not handle:
        handle = GLOBALS.HWND
    # 获取系统缩放比例（默认DPI是96）
    scale_factor = GLOBALS.DPI / 96.0
    # 调整坐标
    scaled_x = int(x * scale_factor)
    scaled_y = int(y * scale_factor)
    scaled_x1 = int(x1 * scale_factor)
    scaled_y1 = int(y1 * scale_factor)
    # 将x和y转化成矩阵，此矩阵表示移动时，鼠标的初始位置
    lParam = win32api.MAKELONG(scaled_x, scaled_y)
    # 将x+x1和y+y1转化成矩阵，此矩阵表示鼠标要移动到的目标位置
    lParam1 = win32api.MAKELONG(scaled_x + scaled_x1, scaled_y + scaled_y1)
    # 按下，移动，抬起
    win32gui.PostMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    win32gui.PostMessage(handle, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lParam1)
    win32gui.PostMessage(handle, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lParam1)
