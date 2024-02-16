import os
import cv2
import numpy as np

# 使用原始字符串或双反斜杠
dir = r".\1"  # 或者 dir = "\\1"

# 确保目录存在
if not os.path.exists(dir):
    print(f"The directory {dir} does not exist.")
else:
    for target_filename in os.listdir(dir):
        target_path = os.path.join(dir, target_filename)
        target_image = cv2.imdecode(np.fromfile(target_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        img = target_image[0:24, 0:38]
        
        # 创建保存图片的目录（如果尚不存在）
        save_dir = r".\card"  # 或者 save_dir = "\\card"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        filename = os.path.join(save_dir, f"{target_filename.replace('.png', '')}.png")
        cv2.imencode('.png', img)[1].tofile(filename)