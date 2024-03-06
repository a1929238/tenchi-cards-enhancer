# 常用方法

import numpy as np
import cv2
import sys
import os

# 读取图片
def imread(filename):
        # 使用 np.fromfile 读取数据
        data = np.fromfile(filename, dtype=np.uint8)
        # 使用 cv2.imdecode() 解码图像数据
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return image
        
# 打包后绝对路径函数
def resource_path(relative_path):
    """获取项目根目录下的资源文件的绝对路径。"""
    # 如果打包，则使用 PyInstaller 的临时目录
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        # 如果未打包，则使用当前文件的目录
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# 隐藏布局内所有控件
def hide_layout(layout):
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget()
        if widget is not None:
            widget.hide()