from module.utils import imread
import numpy as np
import cv2

img = imread("C:/192/code//tenchi-cards-enhancer//error_image28.png")
img = img[:, :2]
cv2.imwrite("..png", img)