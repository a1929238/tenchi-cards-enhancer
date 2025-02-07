# 制作掩膜
import cv2
import numpy as np

from module.utils import imread

img = imread()

result = np.ones_like(img) * 255

result[32:42, 8:] = [0, 0, 0]

result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

cv2.imwrite("result.png", result)
