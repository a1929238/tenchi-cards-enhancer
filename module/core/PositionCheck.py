import numpy as np
from PyQt6.QtCore import QThread

from module.core.DynamicWait import dynamic_wait_areas_to_change
from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match
from module.core.MouseEvent import click
from module.globals.EventManager import event_manager
from module.globals.ResourceInit import resource

COMPOSE_HOUSE_POSITION = (685, 558)
CARD_PRODUCE_POSITION = (108, 260)
CARD_ENHANCE_POSITION = (112, 326)
GEM_ENHANCE_POSITION = (463, 358)
GEM_DECOMPOSE_POSITION = (460, 440)


def check_position() -> str:
    """
    Returns:
        str: 当前位置，一共有5个位置：主菜单, 卡片制作, 卡片强化, 宝石强化, 宝石分解
    """
    # 第一次判断，合成屋图标
    img = get_image(672, 550, 15, 15)
    if direct_img_match(img, resource.compose_icon):
        return "主菜单"
    # 第二次判断，根据XX说明判断目前所处位置
    img = get_image(816, 28, 69, 22)
    if direct_img_match(img, resource.produce_help_icon):
        return "卡片制作"
    elif direct_img_match(img, resource.enhance_help_icon):
        gem_enhance_img = get_image(452, 318, 10, 10)
        if direct_img_match(gem_enhance_img, resource.gem_enhance_not_selected):
            return "卡片强化"
        else:
            return "宝石强化"
    elif direct_img_match(img, resource.decompose_help_icon):
        return "宝石分解"
    return "unknown"


def change_position(target_position, current_position=None):
    """切换位置
    一共有以下位置：主菜单, 卡片制作, 卡片强化, 宝石强化, 宝石分解
    Args:
        current_position(str): 当前位置
        target_position(str): 目标位置
    """
    if current_position is None:
        current_position = check_position()
    if current_position == target_position:
        return
    # 初始化多区域，使用多区域检测来确定位置切换完成
    img_1 = get_image(862, 33, 20, 20)  # 右上角标签位置
    img_2 = get_image(870, 500, 20, 20)   # 右下角卡片位置
    area_1, area_2 = (862, 33, img_1), (870, 500, img_2)

    # 定义点击目标变量
    click_target = None

    match target_position:
        case "主菜单":
            click_target = (913, 39)
        case "卡片制作":
            if current_position == "主菜单":
                click_target = COMPOSE_HOUSE_POSITION
            else:
                click_target = CARD_PRODUCE_POSITION
        case "卡片强化":
            if current_position == "主菜单":
                change_position("卡片制作")
                click_target = CARD_ENHANCE_POSITION
            else:
                click_target = CARD_ENHANCE_POSITION
        case "宝石强化":
            if current_position == "主菜单":
                change_position("卡片制作")
                click_target = GEM_ENHANCE_POSITION
            else:
                click_target = GEM_ENHANCE_POSITION
        case "宝石分解":
            if current_position == "主菜单":
                change_position("卡片制作")
                click_target = GEM_DECOMPOSE_POSITION
            else:
                click_target = GEM_DECOMPOSE_POSITION
    # 点击目标位置
    click(*click_target)
    # 等待位置切换完成
    for _ in range(4):
        if dynamic_wait_areas_to_change(area_1, area_2, interval=50, times=10):
            return True
        # 再次点击目标位置
        click(*click_target)
    else:
        event_manager.show_dialog_signal.emit("位置切换失败！", "为什么位置无法切换？")
        return False
