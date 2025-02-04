from ctypes import windll, create_string_buffer
from ctypes.wintypes import RECT

import numpy as np
from _ctypes import byref
import module.globals.GLOBALS as GLOBALS


def get_image(x, y, width, height):
    """
    从当前窗口句柄获取指定区域的图像。

    参数:
    - x: 区域的左上角x坐标。
    - y: 区域的左上角y坐标。
    - width: 区域的宽度。
    - height: 区域的高度。

    返回:
    - image: 指定区域内包含RGB数据的numpy数组。
    """
    handle = GLOBALS.HWND

    # 获取窗口客户区的大小
    r = RECT()
    windll.user32.GetClientRect(handle, byref(r))
    client_width, client_height = r.right, r.bottom

    # 创建设备上下文
    dc = windll.user32.GetDC(handle)
    cdc = windll.gdi32.CreateCompatibleDC(dc)
    bitmap = windll.gdi32.CreateCompatibleBitmap(dc, client_width, client_height)
    windll.gdi32.SelectObject(cdc, bitmap)

    # 执行位块传输
    windll.gdi32.BitBlt(cdc, 0, 0, client_width, client_height, dc, 0, 0, 0x00CC0020)

    # 准备缓冲区
    total_bytes = client_width * client_height * 4
    buffer = create_string_buffer(total_bytes)
    windll.gdi32.GetBitmapBits(bitmap, total_bytes, buffer)

    # 清理资源
    windll.gdi32.DeleteObject(bitmap)
    windll.gdi32.DeleteObject(cdc)
    windll.user32.ReleaseDC(handle, dc)

    # 转换缓冲区数据为numpy数组
    image = np.frombuffer(buffer, dtype=np.uint8).reshape(client_height, client_width, 4)

    # 裁剪图像到指定区域
    image = image[y:y + height, x:x + width, :3]

    return image
