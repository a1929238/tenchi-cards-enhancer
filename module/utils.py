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
    # 获取当前脚本的绝对路径
    current_script_path = os.path.abspath(__file__)
    # 获取当前脚本所在的目录路径
    current_dir_path = os.path.dirname(current_script_path)
    # 获取根目录路径（假设当前脚本在根目录下的 'module' 文件夹中）
    root_dir_path = current_dir_path
    while not os.path.isfile(os.path.join(root_dir_path, '天知强卡器.py')):
        root_dir_path = os.path.dirname(root_dir_path)
        if os.path.ismount(root_dir_path):
            raise Exception('Failed to find the root directory of the project.')
    
    # 如果打包，则使用 PyInstaller 的临时目录
    base_path = getattr(sys, '_MEIPASS', root_dir_path)
    
    # 构建到资源文件的绝对路径
    return os.path.join(base_path, relative_path)

# 隐藏布局内所有控件
def hide_layout(layout):
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget()
        if widget is not None:
            widget.hide()