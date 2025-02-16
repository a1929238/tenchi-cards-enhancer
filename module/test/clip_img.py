import cv2

from module.utils import imread


def clip_spice_img(img_path):
    """将44X44的原始图像分割成强卡器格式图像"""
    image = imread(img_path)
    image = image[3: 27, 3: 41, :3]
    cv2.imwrite("圣灵香料.png", image)


def clip_card_img(img_path_list):
    """将40X50的原始图像分割成强卡器格式图像"""
    for index, image_path in enumerate(img_path_list):
        image = imread(image_path)
        image = image[19: 34, 4: 37, :3]
        cv2.imwrite(f"{index}.png", image)


path_list = ["冰块冷萃机.png", "微波炉爆弹.png", "梦幻多拿滋.png", "香辣年糕蟹.png"]
clip_card_img(path_list)
