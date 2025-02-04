import random

import numpy as np
import cv2

from module.core.ImgMatch import direct_img_match, template_img_match
from module.globals.ResourceInit import resource

"""
包括剪裁图片，灰度转化，识别数字，输出int等函数
"""


def clip_img(img):
    """
    根据数字剪裁图片
    :param img: numpy 数组，白底黑字的二值图像，白色为 255，黑色为 0
    :return: 剪裁后的 numpy 数组，包含数字的最小边界
    """
    # 找到黑色像素的行列索引
    rows = np.any(img < 255, axis=1)
    cols = np.any(img < 255, axis=0)

    # 计算数字的边界范围
    top, bottom = np.where(rows)[0][[0, -1]]
    left, right = np.where(cols)[0][[0, -1]]

    # 裁剪图像到包含数字的最小矩形区域
    cropped_img = img[top:bottom + 1, left:right + 3]

    return cropped_img


def make_gray(img):
    """
    将RGB图像的纯白色变为黑色，其余变成白色
    :param img: numpy 数组，表示 RGB 图像
    :return: 处理后的 numpy 数组，纯白色变为黑色，其余变为白色
    """
    # 创建描边颜色的掩码，找到所有描边像素，图像的颜色顺序是BGR
    mask = np.all(img == [72, 35, 13], axis=-1)

    # 如果没有描边像素，返回全黑图像
    if not np.any(mask):
        return np.zeros_like(img)

    # 获取描边像素的行列坐标
    rows = np.where(mask)[0]
    cols = np.where(mask)[1]

    # 计算最小矩形边界
    min_row, max_row = rows.min(), rows.max()
    min_col, max_col = cols.min(), cols.max()

    # 裁剪图像至最小矩形区域
    img = img[min_row:max_row + 1, min_col:max_col + 1]

    # 创建一个新图像副本
    result = np.ones_like(img) * 255  # 将所有像素设为白色

    # 找到纯白色像素的位置
    white_pixels = np.all(img == 255, axis=-1)

    # 将纯白色像素变为黑色
    result[white_pixels] = [0, 0, 0]

    return result


def get_num(img, num_images: dict):
    """
    识别图中数字，返回识别结果
    :param img: numpy 数组，待识别的图像
    :param num_images: 包含数字0-9和01的图像的字典，每个图像为 numpy 数组
    :return: 识别的数字（int 类型）
    """
    # 将图像变为灰度图
    img = make_gray(img)

    # 裁剪图像
    img = clip_img(img)

    # 初始步长
    width = 7

    # 初始化索引和结果字符串
    i = 0
    result = ""

    # 使用 while 循环，手动控制步长
    while i < img.shape[1]:
        # 提取待识别的数字图像部分
        num_part = img[:, i:i + width]
        # 舍弃余数部分
        if num_part.shape[1] < width:
            break
        # 对比 num_img_list 中的数字图像，找到最匹配的数字
        for num, num_img in num_images.items():
            # 当1在第一位时，做特殊处理
            if i == 0 and num == "01":
                extra_num_part = num_part[:, :-1]
                if direct_img_match(extra_num_part, num_img):
                    result += "1"
                    i -= 1
                    break
            # 如果数字部分和当前数字图像匹配，则记录数字
            elif direct_img_match(num_part, num_img):
                result += str(num)
                break
        else:
            # 识别均失败则尝试使用模版匹配再匹配一轮
            for num, num_img in resource.num_images_without_hash.items():
                # 当1在第一位时，做特殊处理
                if i == 0 and num == "01":
                    extra_num_part = num_part[:, :-1]
                    if template_img_match(extra_num_part, num_img, with_click=False, threshold=0.97):
                        result += "1"
                        i -= 1
                        break
                # 如果数字部分和当前数字图像匹配，则记录数字
                elif template_img_match(num_part, num_img, with_click=False, threshold=0.97):
                    if num == "01":
                        result += "1"
                        break
                    result += str(num)
                    break
            else:
                # 还是失败，油尽灯枯，保存错误图像
                print("识别失败，保存错误图像")
                cv2.imwrite(f"error_image{i}.png", num_part)
                cv2.imwrite(f"error_image{i}_full.png", img)

        # 更新索引
        i += width

    # 返回识别的数字（整数形式）
    return int(result) if result else None
