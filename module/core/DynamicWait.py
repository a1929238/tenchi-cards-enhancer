from PyQt6.QtCore import QThread

from module.core.CardEnhancer import is_card_placed
from module.core.GetImg import get_image
from module.core.ImgMatch import has_area_changed, direct_img_match, screenshot_and_direct_img_match
from module.core.MouseEvent import click
from module.globals.ResourceInit import resource


def dynamic_check_gold(interval=200, times=4, with_click=False, click_pos=None):
    """
    通过多次检测金币有无变化，来实现动态等待
    可在检测的间隔中点击对应位置
    Args:
        interval: 区域检测间隔时间，默认200ms
        times: 检测轮数，默认4次
        with_click: 是否在检测间隔中点击对应位置，默认False
        click_pos: 点击位置，默认None
    """
    for _ in range(times):
        if has_area_changed(860, 555, 45, 10, interval):
            return True
        if with_click:
            click(*click_pos)
    return False


def dynamic_wait_gem_enhance_btn_to_gry(interval=200, times=10) -> bool:
    for _ in range(times):
        if screenshot_and_direct_img_match(261, 423, resource.gray_gem_enhance_btn):
            return True
        QThread.msleep(interval)
    return False


def dynamic_wait_areas_to_change(*areas, interval=200, times=10) -> bool:
    """
    动态等待，直到任意目标区域与对应图像不同
    任意位置变化后都将返回True
    Args:
        *areas: (x, y, img)元组组成的可变参数
        interval: 检测间隔时间，默认200ms
        times: 检测次数，默认10次
    """
    x = []
    y = []
    width = []
    height = []
    img_hash = []
    for index, area in enumerate(areas):
        x.append(area[0])
        y.append(area[1])
        width.append(area[2].shape[1])
        height.append(area[2].shape[0])
        img_hash.append(hash(area[2].tobytes()))
    for _ in range(times):
        for index, area in enumerate(areas):
            current_img = get_image(x[index], y[index], width[index], height[index])
            if not direct_img_match(current_img, img_hash[index]):
                QThread.msleep(100)
                return True
        QThread.msleep(interval)
    return False


def dynamic_wait_card_slot_state(card_index, state, interval=100, times=80) -> bool:
    """
    动态等待目标卡槽是否为目标状态
    Args:
        card_index: 卡槽索引，2,3,4
        state: 目标状态，True表示有卡，False表示无卡
        interval: 检测间隔时间，默认50ms
        times: 检测次数，默认80次
    """
    for _ in range(times):
        if is_card_placed(card_index) == state:
            return True
        QThread.msleep(interval)
    return False
