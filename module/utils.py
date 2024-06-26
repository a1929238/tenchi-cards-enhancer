# 常用方法

import numpy as np
import cv2
import sys
import os

# 读取图片
def imread(filename, with_alpha=False):
        # 使用 np.fromfile 读取数据
        data = np.fromfile(filename, dtype=np.uint8)
        # 使用 cv2.imdecode() 解码图像数据
        if with_alpha:
            image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        else:
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return image
        
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

# 隐藏布局内所有控件
def hide_layout(layout):
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget()
        if widget is not None:
            widget.hide()

def template_match_with_mask(img, tar_img):
    # 宝石的目标图片只有8位深度，先转化为32位的
    # 图片带有透明度通道，先将透明度部分转化为掩码
    mask = tar_img[:, :, 3]
    # 再只取前三个通道
    img = img[:, :, :3]
    tar_img = tar_img[:, :, :3]
    result = cv2.matchTemplate(img, tar_img, cv2.TM_CCORR_NORMED, mask=mask)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= 0.99:
        return True
    else:
        return False