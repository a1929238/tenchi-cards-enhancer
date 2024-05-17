import time
from typing import Union

import cv2
import numpy as np

from module.bg_img_screenshot import capture_image_png, png_cropping


def match_template_with_optional_mask(img_source, img_template) -> np.ndarray:
    """
    使用可选掩模进行模板匹配。

    如果模板图像包含Alpha通道且不是纯白，则使用该Alpha通道作为掩模进行匹配。
    如果模板图像不包含Alpha通道或Alpha通道为纯白，则直接进行匹配。

    Args:
        img_source (numpy.ndarray): 源图像。
        img_template (numpy.ndarray): 模板图像，可能包含Alpha通道作为掩模。

    Returns:
        numpy.ndarray: 匹配结果。
    """
    """
    函数:对应方法 匹配良好输出->匹配不好输出
    CV_TM_SQDIFF:平方差匹配法 [1]->[0]；
    CV_TM_SQDIFF_NORMED:归一化平方差匹配法 [0]->[1]；
    CV_TM_CCORR:相关匹配法 [较大值]->[0]；
    CV_TM_CCORR_NORMED:归一化相关匹配法 [1]->[0]；
    CV_TM_CCOEFF:系数匹配法；
    CV_TM_CCOEFF_NORMED:归一化相关系数匹配法 [1]->[0]->[-1]
    """
    method = cv2.TM_SQDIFF_NORMED

    # 检查模板图像是否包含Alpha通道
    if img_template.shape[2] == 4:
        # 提取Alpha通道作为掩模
        mask = img_template[:, :, 3]
        # 移除Alpha通道，保留RGB部分
        img_template = img_template[:, :, :3]

        # 检查掩模是否为纯白
        if not np.all(mask == 255):
            # 掩模非纯白，使用掩模进行匹配
            result = cv2.matchTemplate(image=img_source, templ=img_template, method=method, mask=mask)
            return result

    # 对于不包含Alpha通道或Alpha通道为纯白的情况，直接进行匹配
    result = cv2.matchTemplate(image=img_source, templ=img_template, method=method)
    return result


def match_p_in_w(
        source_handle,
        source_range: list,
        template,
        match_tolerance: float = 0.95,
        is_test=False,
        source_root_handle=None) -> Union[None, list]:
    """
    find target in template
    catch an image by a handle, find a smaller image(target) in this bigger one, return center relative position
    :param source_handle: 窗口句柄
    :param source_range: 原始图像生效的范围,为 [左上X, 左上Y,右下X, 右下Y], 右下位置超出范围取最大(不会报错)
    :param template: 目标图片的文件路径
    :param match_tolerance: 捕捉准确度阈值 0-1
    :param is_test: 仅单例测试使用, 显示匹配到的最右图像位置框
    :param source_root_handle: 根窗口句柄, 用于检查窗口是否最小化, 如果最小化则尝试恢复至激活窗口的底层 可空置

    Returns: 识别到的目标的中心坐标(相对于截图后)
    """

    # 截取原始图像(windows窗口) BGRA -> BGR
    img_source = capture_image_png(handle=source_handle, raw_range=source_range, root_handle=source_root_handle)
    img_source = img_source[:, :, :3]

    # 根据 路径 或者 numpy.array 选择是否读取
    if type(template) is np.ndarray:
        img_template = template
    else:
        # 读取目标图像,中文路径兼容方案
        img_template = cv2.imdecode(buf=np.fromfile(file=template, dtype=np.uint8), flags=-1)

    # 自定义的模板匹配
    result = match_template_with_optional_mask(img_source=img_source, img_template=img_template)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(src=result)

    # 如果匹配度<阈值，就认为没有找到
    if minVal >= 1 - match_tolerance:
        return None

    # 最优匹配的左上坐标
    (start_x, start_y) = minLoc

    # 输出识别到的中心
    center_point = [
        start_x + int(img_template.shape[1] / 2),
        start_y + int(img_template.shape[0] / 2)
    ]

    # 测试时绘制边框
    if is_test:
        img_source = img_source.astype(np.uint8)
        # 确定起点和终点的(x，y)坐标边界框
        end_x = start_x + img_template.shape[1]
        end_y = start_y + img_template.shape[0]
        # 在图像上绘制边框
        cv2.rectangle(
            img=img_source,
            pt1=(start_x, start_y),
            pt2=(end_x, end_y),
            color=(0, 0, 255),
            thickness=1)
        # 显示输出图像
        cv2.imshow(
            winname="SourceImg.png",
            mat=img_source)
        cv2.waitKey(0)

    return center_point


def match_ps_in_w(
        source_handle,
        template_opts: list,
        return_mode: str,
        source_root_handle=None) -> Union[None, list]:
    """
    一次截图中找复数的图片, 性能更高的写法
    :param source_handle: 窗口句柄
    :param template_opts: [{"template":str,"source_range": [x1:int,y1:int,x2:int,y2:int],"match_tolerance":float},...]
    :param return_mode: 模式 and 或者 or
    :param source_root_handle: 根窗口句柄, 用于检查窗口是否最小化, 如果最小化则尝试恢复至激活窗口的底层 可空置
    :return: 通过了mode, 则返回[{"x":int,"y":int},None,...] , 否则返回None

    """
    # 截屏
    source_img = capture_image_png(handle=source_handle, raw_range=[0, 0, 3000, 3000], root_handle=source_root_handle)
    result_list = []

    for p in template_opts:

        source_range = png_cropping(image=source_img, raw_range=p["source_range"])  # 裁剪
        template = p["template"]  # 目标
        match_tolerance = p["match_tolerance"]  # 目标精准度阈值

        if type(template) is np.ndarray:
            template_img = template
        else:
            # 读取目标图像,中文路径兼容方案, (行,列,ABGR)
            template_img = cv2.imdecode(
                np.fromfile(
                    file=template,
                    dtype=np.uint8),
                -1)

        # 执行模板匹配，采用的匹配方式cv2.TM_SQDIFF_NORMED
        result = cv2.matchTemplate(
            image=source_range[:, :, :-1],
            templ=template_img[:, :, :-1],
            method=cv2.TM_SQDIFF_NORMED)

        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(src=result)

        # 如果匹配度小于X%，就认为没有找到
        if minVal > 1 - match_tolerance:
            result_list.append(None)
            continue

        # 最优匹配的左上坐标
        (start_x, start_y) = minLoc

        # 输出识别到的中心
        result_list.append(
            [
                start_x + int(template_img.shape[1] / 2),
                start_y + int(template_img.shape[0] / 2)
            ]
        )

    if return_mode == "and":
        if None in result_list:
            return None
        else:
            return result_list
    elif return_mode == "or":
        if all(i is None for i in result_list):
            return None
        else:
            return result_list


def loop_match_p_in_w(
        source_handle,
        source_range: list,
        template,
        match_tolerance: float = 0.95,
        match_interval: float = 0.2,
        match_failed_check: float = 10,
        after_sleep: float = 0.05,
        click: bool = True,
        click_function= None,
        after_click_template=None,
        source_root_handle=None,
) -> bool:
    """
    catch a resource by a handle, find a smaller resource in the bigger one,
    click the center of the smaller one in the bigger one by handle(relative position)
    Args:
        :param source_handle: 截图句柄
        :param source_range: 截图后截取范围 [左上x,左上y,右下x,右下y]
        :param template: 目标图片路径
        :param match_tolerance: 捕捉准确度阈值 0-1
        :param match_interval: 捕捉图片的间隔
        :param match_failed_check: # 捕捉图片时间限制, 超时输出False
        :param after_sleep: 找到图/点击后 的休眠时间
        :param click: 是否点一下
        :param after_click_template: 点击后进行检查, 若能找到该图片, 视为无效, 不输出True, 继承前者的精准度tolerance
        :param source_root_handle: 根窗口句柄, 用于检查窗口是否最小化, 如果最小化则尝试恢复至激活窗口的底层 可空置

    return:
        是否在限定时间内找到图片

    """
    spend_time = 0.0
    while True:

        find_target = match_p_in_w(
            source_handle=source_handle,
            source_range=source_range,
            template=template,
            match_tolerance=match_tolerance,
            source_root_handle=source_root_handle)

        if find_target:

            if not click:
                time.sleep(after_sleep)

            else:
                click_function(
                    handle=source_handle,
                    x=find_target[0] + source_range[0],
                    y=find_target[1] + source_range[1]
                )
                time.sleep(after_sleep)

                if after_click_template:
                    find_target = match_p_in_w(
                        source_handle=source_handle,
                        source_range=source_range,
                        template=after_click_template,
                        match_tolerance=match_tolerance,
                        source_root_handle=source_root_handle)
                    if find_target:
                        continue  # 当前状态没有产生变化, 就不进行输出

            return True

        # 超时, 查找失败
        time.sleep(match_interval)
        spend_time += match_interval
        if spend_time > match_failed_check:
            return False


def loop_match_ps_in_w(
        source_handle,
        template_opts: list,
        return_mode: str,
        match_failed_check: float = 10,
        match_interval: float = 0.2,
        source_root_handle=None,
) -> bool:
    """
        :param source_handle: 截图句柄
        :param template_opts: [{"template":str,"source_range": [x1:int,y1:int,x2:int,y2:int],"match_tolerance":float},...]
        :param return_mode: 模式 and 或者 or
        :param match_interval: 捕捉图片的间隔
        :param match_failed_check: # 捕捉图片时间限制, 超时输出False
        :return: 通过了mode, 则返回[{"x":int,"y":int},None,...] , 否则返回None
        :param source_root_handle: 根窗口句柄, 用于检查窗口是否最小化, 如果最小化则尝试恢复至激活窗口的底层 可空置
        """
    # 截屏
    invite_time = 0.0
    while True:
        find_target = match_ps_in_w(
            source_handle=source_handle,
            template_opts=template_opts,
            return_mode=return_mode,
            source_root_handle=source_root_handle)
        if find_target:
            return True

        # 超时, 查找失败
        invite_time += match_interval
        time.sleep(match_interval)
        if invite_time > match_failed_check:
            return False
