import random

import numpy as np
import cv2

from module.core.ImgMatch import direct_img_match, template_img_match
from module.globals.ResourceInit import resource
from module.log.TenchiLogger import logger

"""
包括剪裁图片，灰度转化，识别数字，输出int等函数
"""


def clip_img(img):
    """
    根据数字剪裁图片
    :param img: numpy 数组，白底黑字的二值图像，白色为 255，黑色为 0
    :return: 剪裁后的 numpy 数组，去除了所有空格的数字图像
    """
    # 找到黑色像素的行列索引
    rows = np.any(img < 255, axis=1)
    cols = np.any(img < 255, axis=0)

    # 计算数字的边界范围
    top, bottom = np.where(rows)[0][[0, -1]]
    left, right = np.where(cols)[0][[0, -1]]

    # 裁剪图像到包含数字的最小矩形区域
    img = img[top:bottom + 1, left:right + 1]
    # 去除小于等于1个黑色像素的列
    # 计算每一列的黑色像素数量（小于255的值）
    black_pixels_per_col = np.sum(img < 255, axis=0)
    # 找到黑色像素数量大于1的列的索引
    cols_to_keep = np.where(black_pixels_per_col > 1)[0]
    # 使用这些索引来切片图像，只保留符合条件的列
    img = img[:, cols_to_keep]
    # 再去除小于等于1个黑色像素的行
    black_pixels_per_row = np.sum(img < 255, axis=1)
    rows_to_keep = np.where(black_pixels_per_row > 1)[0]
    img = img[rows_to_keep, :]

    return img


def make_gray(img):
    """
    将RGB图像的纯白色变为黑色，其余变成白色
    :param img: numpy 数组，表示 RGB 图像
    :return: 处理后的 numpy 数组，纯白色变为黑色，其余变为白色
    """
    # 创建描边颜色的掩码，找到所有描边像素，图像的颜色顺序是BGR
    mask = np.all(img == [72, 35, 13], axis=-1)

    # 如果没有描边像素，返回None
    if not np.any(mask):
        return None

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

    # 如果不存在纯白色像素，返回None
    if not np.any(white_pixels):
        return None

    # 将纯白色像素变为黑色
    result[white_pixels] = [0, 0, 0]

    # 将图像转化为灰度图像
    result = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)

    return result


def get_num(img):
    """
    识别图中数字，返回识别结果
    :param img: numpy 数组，待识别的图像
    :return: 识别的数字（int 类型）
    """
    # 将图像变为灰度图
    img = make_gray(img)

    if img is None:
        return None

    # 裁剪图像
    img = clip_img(img)

    # 图像如果为空列表，就直接返回None
    if img.size == 0:
        return None

    # 初始化索引和结果字符串
    i = 0
    result = ""

    # 使用 while 循环，手动控制步长
    while i < img.shape[1]:
        matched = False
        # 尝试匹配所有可能宽度的数字
        for width, digit, num_img in resource.num_images:
            # 如果剩余区域小于当前宽度，则跳过当前数字
            if i + width > img.shape[1]:
                continue

            # 提取当前宽度的图像区域
            num_part = img[:, i:i + width]

            # 直接匹配当前宽度
            if direct_img_match(num_part, num_img):
                result += digit
                i += width  # 按实际宽度步进
                matched = True
                break
        if not matched:
            # 识别均失败则尝试使用模版匹配再匹配一轮
            for width, digit, num_img in resource.num_images_without_hash:
                # 如果剩余区域小于当前宽度，则跳过当前数字
                if i + width > img.shape[1]:
                    continue
                num_part = img[:, i:i + width]
                # 确认数字部分不能小于模版部分
                if num_img.shape[1] > num_part.shape[1] or num_img.shape[0] > num_part.shape[0] :
                    continue
                # 如果数字部分和当前数字图像匹配，则记录数字
                if template_img_match(num_part, num_img, threshold=0.9):
                    result += digit
                    i += width
                    break
            else:
                # 还是失败，往后推进1像素
                logger.debug("识别失败，往后推进1像素")

                # 保证至少推进1像素
                i += 1

    # 返回识别的数字（整数形式）
    return int(result) if result else None
