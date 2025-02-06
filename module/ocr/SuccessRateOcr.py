import numpy as np
import cv2

from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match
from module.globals.ResourceInit import resource

SUCCESS_RATE_AREA = (358, 464, 61, 10)


def get_success_rate():
    """
    用ocr的方式获取原始成功率和成功率加成
    保存的数字图片在字典中的键都是两位的str，前一位表示宽度，后一位表示数字
    """
    # 获取成功率图片
    success_rate_img = get_image(*SUCCESS_RATE_AREA)
    # 将图片转化为灰度图像
    success_rate_img = make_gray(success_rate_img)
    # 裁剪图片，去除所有存在纯白像素的列
    success_rate_img = clip_img(success_rate_img)

    # 初始化索引和结果字符串
    i = 0
    result = ""

    while i < success_rate_img.shape[1]:
        matched = False

        # 尝试匹配所有可能宽度的数字
        for width, digit, num_img in resource.success_rate_num_images:
            # 最后一格的数字均在最右侧少了一列，将不是句号的数字裁剪掉
            if i >= 40 and digit != ".":
                num_img = num_img[:, :-1]

            # 提取当前宽度的图像区域
            num_part = success_rate_img[:, i:i + width]

            # 直接匹配当前宽度
            if direct_img_match(num_part, hash(num_img.tobytes())):
                result += digit
                i += width  # 按实际宽度步进
                matched = True
                break

        # 匹配失败处理
        if not matched:
            # 保存错误图像（使用最大步长作为错误窗口）
            error_part = success_rate_img[:, i:i + 6]
            error_part2 = success_rate_img[:, i:i + 5]
            if error_part.shape[1] > 0:  # 避免空图像
                cv2.imwrite(f"error_image{i}.png", error_part)
                cv2.imwrite(f"error_image{i}2.png", error_part2)
                cv2.imwrite(f"error_image{i}_full.png", success_rate_img)

            # 保证至少推进1像素
            i += 1
    if result:
        # 处理字符串
        result = result.replace('%', '')  # 移除百分号
        # 分割字符串
        num1, num2 = result.split('+')
    else:
        return 0, 0
    return float(num1), float(num2)


def make_gray(img):
    """
    将RGB图像的文字颜色变为黑色，其余变成白色
    :param img: numpy 数组，表示 RGB 图像
    :return: 处理后的 numpy 数组，文字颜色变为黑色，其余变为白色
    """
    # 创建一个新图像副本
    result = np.ones_like(img) * 255  # 将所有像素设为白色

    # 找到文字的像素位置
    words_pixels = np.all(img == [137, 211, 245], axis=-1)

    # 将纯白色像素变为黑色
    result[words_pixels] = [0, 0, 0]

    # 将图像转化为灰度图像
    result = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)

    return result


def clip_img(img):
    """
    根据数字剪裁图片
    :param img: numpy 数组，白底黑字的二值图像，白色为 255，黑色为 0
    :return: 剪裁后的 numpy 数组，包含数字的最小边界，同时去除了所有纯白色的列
    """
    # 找到黑色像素的行列索引
    rows = np.any(img < 255, axis=1)
    cols = np.any(img < 255, axis=0)

    # 计算数字的边界范围
    top, bottom = np.where(rows)[0][[0, -1]]
    left, right = np.where(cols)[0][[0, -1]]

    # 裁剪图像到包含数字的最小矩形区域
    img = img[top:bottom + 1, left:right + 1]

    # 去除所有纯白色像素的列
    non_white_cols = np.any(img < 255, axis=0)  # 找到非全白的列
    img = img[:, non_white_cols]  # 保留非全白的列

    return img
