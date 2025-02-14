import numpy as np
import cv2
from PyQt6.QtCore import QThread

from module.core.GetImg import get_image
from module.core.MouseEvent import click


def screenshot_and_direct_img_match(x, y, tar_img) -> bool:
    """
    在屏幕上根据给定的左上角坐标和目标图片尺寸进行截图，并执行精确像素级图像比对。

    该函数会以(x,y)为左上角坐标，按照目标图片的宽高截取屏幕区域，随后将截图与目标图片进行逐像素比对。

    Args:
        x (int): 截图区域左上角的X坐标（像素单位）
        y (int): 截图区域左上角的Y坐标（像素单位）
        tar_img (PIL.Image.Image): 目标图片对象，该图片的尺寸将决定截图范围，并作为比对基准

    Returns:
        bool: 当屏幕截图区域与目标图片的像素完全一致时返回True，否则返回False

    Note:
        比对结果受屏幕缩放比例、图像色彩模式等因素影响，请确保比对图片与屏幕截图参数一致
    """
    # 得到目标图片的宽高
    height, width = tar_img.shape[:2]
    # 截图
    img = get_image(x, y, width, height)
    # 哈希化目标图片
    tar_img_hash = hash(tar_img.tobytes())
    return direct_img_match(img, tar_img_hash)


def direct_img_match(img, tar_img_hash) -> bool:
    """
    通过哈希比对来判断两个图像是否完全相同。

    Args:
        img: numpy数组
        tar_img_hash: 哈希值

    Returns:
        bool: 如果两图完全相同返回True，否则返回False
    """
    # 使用哈希进行高效比对
    return hash(img.tobytes()) == tar_img_hash


def template_img_match(img, tar_img, threshold=0.95,
                       with_click=False, origin_pos=None, with_mask=False, extra_mask=None) -> bool:
    """
    使用模板匹配算法进行图像匹配，可以在匹配成功后点击匹配到的图像中央

    Args:
        img(numpy.ndarray): numpy数组
        tar_img(numpy.ndarray): numpy数组
        threshold(float): 匹配阈值，默认为0.95，表示匹配成功所需的相似度
        with_click(bool): 是否在匹配成功后点击匹配到的图像中央，默认为False
        origin_pos(Tuple): 图像左上角位置，用于点击
        with_mask(bool): 是否使用目标图像本身的透明度通道作为掩码进行匹配，默认为False
        extra_mask(numpy.ndarray): 额外掩码，用于对目标图像进行掩码处理，默认为None

    Returns:
        bool: 如果匹配成功返回True，否则返回False
    """
    # 通道数检查
    if with_mask and (tar_img.ndim != 3 or tar_img.shape[2] != 4):
        raise ValueError("tar_img must be RGBA image when with_mask=True")
    if with_mask:
        # 将目标图像的透明度通道作为掩码
        mask = tar_img[:, :, 3]
        # 叠加上基础掩码
        if extra_mask is not None:
            extra_mask = extra_mask[:, :, 0]
            mask = cv2.bitwise_and(mask, extra_mask)
    else:
        mask = None
    # 只取前三个通道
    img = img[..., :3] if img.ndim == 3 else img
    tar_img = tar_img[..., :3] if tar_img.ndim == 3 else tar_img
    # 进行模板匹配
    result = cv2.matchTemplate(img, tar_img, cv2.TM_CCORR_NORMED, mask=mask)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        if with_click:
            # 计算目标图像的宽高
            h, w = tar_img.shape[:2]
            # 计算匹配区域的中心坐标
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            # 加上原点坐标
            center_x += origin_pos[0] if origin_pos else 0
            center_y += origin_pos[1] if origin_pos else 0
            # 调用点击方法
            click(center_x, center_y)
        return True
    else:
        return False


def find_and_crop_template(img, tar_img, threshold=0.95, extra_mask=None):
    """
    使用模板匹配找到目标图像中的模板区域，并裁剪出该区域。

    Args:
        img: 图像。
        tar_img : 目标图像
        threshold (float): 匹配阈值，范围为0到1，默认为0.8
        extra_mask (numpy.ndarray): 额外掩码，用于对目标图像进行掩码处理，默认为None

    Returns:
        cropped_image (numpy.ndarray): 裁剪出的目标区域图像。
        None: 如果没有找到匹配区域，则返回None。
    """

    # 获取模板图像的尺寸
    h, w = tar_img.shape[:2]

    if extra_mask is not None:
        # 将目标图像的透明度通道作为掩码
        mask = tar_img[:, :, 3]
        # 叠加上基础掩码
        extra_mask = extra_mask[:, :, 0]
        mask = cv2.bitwise_and(mask, extra_mask)
    else:
        mask = None
    # 只取前三个通道
    img = img[..., :3] if img.ndim == 3 else img
    tar_img = tar_img[..., :3] if tar_img.ndim == 3 else tar_img

    # 进行模板匹配
    result = cv2.matchTemplate(img, tar_img, cv2.TM_CCORR_NORMED, mask=mask)

    # 找到匹配结果中的最大值及其位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 如果匹配度超过阈值，则裁剪出目标区域
    if max_val >= threshold:
        # 获取匹配区域的左上角和右下角坐标
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # 裁剪出目标区域
        cropped_image = img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

        # 制作目标区域下半部分的元组，用于后续的数字识别操作
        area = (top_left[0], top_left[1] + h // 2, w, h // 2)

        return cropped_image, area


def has_area_changed(x, y, width, height, interval=200, times=10) -> bool:
    """
    循环截图并比对同一区域，判断图片有没有发生变化
    """
    # 初始截图作为前一张图
    img = hash(get_image(x, y, width, height).tobytes())

    for _ in range(times):
        # 等待指定间隔
        QThread.msleep(interval)
        # 获取当前截图
        current_img = get_image(x, y, width, height)

        # 比较当前截图与前一张截图
        if not direct_img_match(current_img, img):
            return True

    # 所有轮次比较后无变化
    return False
