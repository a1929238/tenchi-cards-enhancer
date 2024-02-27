# 常用方法

import numpy as np
import cv2

# 读取图片
def imread(filename):
        # 使用 np.fromfile 读取数据
        data = np.fromfile(filename, dtype=np.uint8)
        # 使用 cv2.imdecode() 解码图像数据
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return image