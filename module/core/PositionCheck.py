import cv2
import numpy as np
from PyQt6.QtCore import QThread

from module.core.DynamicWait import dynamic_wait_areas_to_change
from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match
from module.core.MouseEvent import click
from module.globals import GLOBALS
from module.globals.EventManager import event_manager
from module.globals.ResourceInit import resource

COMPOSE_HOUSE_POSITION = (685, 558)
CARD_PRODUCE_POSITION = (108, 260)
CARD_ENHANCE_POSITION = (112, 326)
GEM_ENHANCE_POSITION = (463, 358)
GEM_DECOMPOSE_POSITION = (460, 440)

position_icon_mapping = {
    "主菜单": ((672, 550, 15, 15), resource.compose_icon),
    "卡片制作": ((816, 28, 69, 22), resource.produce_help_icon),
    "卡片强化": ((816, 28, 69, 22), resource.enhance_help_icon),
    "宝石强化": ((816, 28, 69, 22), resource.enhance_help_icon),
    "宝石分解": ((816, 28, 69, 22), resource.decompose_help_icon)
}


def check_position(expect_position=None) -> str:
    """
    Args:
        expect_position(str): 预期位置
    Returns:
        str: 当前位置，一共有5个位置：主菜单, 卡片制作, 卡片强化, 宝石强化, 宝石分解
    """
    if expect_position:
        area, icon = position_icon_mapping[expect_position]
        img = get_image(*area)
        if direct_img_match(img, icon):
            return expect_position
        else:
            return "unknown"
    for position, (area, icon) in position_icon_mapping.items():
        img = get_image(*area)
        if direct_img_match(img, icon):
            if "强化" in position:
                gem_enhance_img = get_image(452, 318, 10, 10)
                if direct_img_match(gem_enhance_img, resource.gem_enhance_not_selected):
                    return "卡片强化"
                else:
                    return "宝石强化"
            return position
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
    for _ in range(20):
        QThread.msleep(100)
        if check_position(target_position) == target_position:
            return True
        if not GLOBALS.IS_RUNNING:
            return False
        if target_position != "主菜单":
            click(*click_target)
    else:
        event_manager.show_dialog_signal.emit("位置切换失败！", "为什么位置无法切换？")
        return False
