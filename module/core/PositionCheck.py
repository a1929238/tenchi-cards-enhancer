import numpy as np
from PyQt6.QtCore import QThread

from module.core.DynamicWait import dynamic_wait_areas_to_change
from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match
from module.core.MouseEvent import click
from module.globals.ResourceInit import resource


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
    # compose_position_list = ["卡片制作", "卡片强化", "宝石强化", "宝石分解"]
    # 初始化多区域，使用多区域检测来确定位置切换完成
    img_1 = get_image(862, 33, 20, 20)  # 右上角标签位置
    img_2 = get_image(870, 500, 20, 20)   # 右下角卡片位置
    area_1, area_2 = (862, 33, img_1), (870, 500, img_2)
    compose_house_position = (685, 558)
    card_produce_position = (108, 260)
    card_enhance_position = (112, 326)
    gem_enhance_position = (463, 358)
    gem_decompose_position = (460, 440)
    match target_position:
        case "主菜单":
            click(913, 39)
        case "卡片制作":
            if current_position == "主菜单":
                click(*compose_house_position)
            else:
                click(*card_produce_position)
        case "卡片强化":
            if current_position == "主菜单":
                change_position("主菜单", "卡片制作")
                click(*card_enhance_position)
            else:
                click(*card_enhance_position)
        case "宝石强化":
            if current_position == "主菜单":
                change_position("主菜单", "卡片制作")
                click(*gem_enhance_position)
            else:
                click(*gem_enhance_position)
        case "宝石分解":
            if current_position == "主菜单":
                change_position("主菜单", "卡片制作")
                click(*gem_decompose_position)
            else:
                click(*gem_decompose_position)

    # 等待位置切换完成
    if dynamic_wait_areas_to_change(area_1, area_2):
        return True
    else:
        return False
